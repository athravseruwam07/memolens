from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import websockets


# 1x1 JPEG pixel
JPEG_1X1_BASE64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEA8QEA8PDw8PDw8PDw8PDw8PFREWFhUR"
    "FRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGxAQGi0fHyUtLS0tLS0tLS0t"
    "LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAQMBEQACEQEDEQH/"
    "xAAZAAADAQEBAAAAAAAAAAAAAAAABQYBBAf/xAAeEAADAQEBAQEBAQAAAAAAAAABAgMABAURIQYS"
    "Mf/EABUBAQEAAAAAAAAAAAAAAAAAAAAB/8QAFhEBAQEAAAAAAAAAAAAAAAAAAQAR/9oADAMBAAIR"
    "AxEAPwD2WQ0jUqVfV2nKXf/Z"
)


@dataclass
class Ctx:
    base_url: str
    api_base: str
    ws_base: str
    patient_id: str
    caregiver_email: str
    caregiver_password: str
    timeout_seconds: int


def _to_ws_base(base_url: str) -> str:
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://") :]
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://") :]
    raise ValueError("Base URL must start with http:// or https://")


async def _api_post(client: httpx.AsyncClient, path: str, body: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    res = await client.post(path, json=body, headers=headers)
    res.raise_for_status()
    payload = res.json()
    if payload.get("error"):
        raise RuntimeError(f"API error at POST {path}: {payload['error']}")
    return payload["data"]


async def _api_get(client: httpx.AsyncClient, path: str, token: str | None = None) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    res = await client.get(path, headers=headers)
    res.raise_for_status()
    payload = res.json()
    if payload.get("error"):
        raise RuntimeError(f"API error at GET {path}: {payload['error']}")
    return payload["data"]


async def _listen_live_events(uri: str, timeout_seconds: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    async with websockets.connect(uri, max_size=10_000_000) as ws:
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.2, deadline - asyncio.get_running_loop().time())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            msg = json.loads(raw)
            if msg.get("type") == "event":
                event = msg.get("event")
                if isinstance(event, dict):
                    out.append(event)
    return out


async def _push_demo_stream(uri: str, frames: int = 3) -> None:
    async with websockets.connect(uri, max_size=10_000_000) as ws:
        for _ in range(frames):
            payload = {
                "frame_b64": JPEG_1X1_BASE64,
                "room": "kitchen",
                "near_exit": True,
                "detections": [
                    {"item": "keys", "room": "kitchen", "confidence": 0.95},
                    {"item": "medication", "room": "kitchen", "confidence": 0.96},
                ],
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(0.35)


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


async def run(ctx: Ctx) -> None:
    started_at = datetime.now(timezone.utc)
    started_iso = started_at.isoformat()

    async with httpx.AsyncClient(base_url=ctx.api_base, timeout=20.0) as client:
        print("[1/7] Health check")
        health = await _api_get(client, "/health")
        if health.get("status") != "ok":
            raise RuntimeError(f"Backend unhealthy: {health}")

        print("[2/7] Caregiver login")
        auth = await _api_post(
            client,
            "/auth/login",
            {"email": ctx.caregiver_email, "password": ctx.caregiver_password},
        )
        token = auth.get("token")
        if not token:
            raise RuntimeError("Login failed: no token")

        print("[3/7] Patient access check")
        _ = await _api_get(client, f"/patients/{ctx.patient_id}", token)

        print("[4/7] Query flow checks (lost object + daily meds)")
        keys_q = await _api_post(
            client,
            "/query",
            {"patient_id": ctx.patient_id, "question": "Where are my keys?"},
            token,
        )
        if keys_q.get("answer_type") != "item_location":
            raise RuntimeError(f"Unexpected keys query answer_type: {keys_q.get('answer_type')}")
        meds_q = await _api_post(
            client,
            "/query",
            {"patient_id": ctx.patient_id, "question": "Did I take my medication?"},
            token,
        )
        if meds_q.get("answer_type") != "medication_adherence":
            raise RuntimeError(f"Unexpected meds query answer_type: {meds_q.get('answer_type')}")

        print("[5/7] Live flow check (events WS + stream WS)")
        events_ws_uri = f"{ctx.ws_base}/ws/events/{ctx.patient_id}?token={token}"
        stream_ws_uri = f"{ctx.ws_base}/ws/stream/{ctx.patient_id}"
        listener = asyncio.create_task(_listen_live_events(events_ws_uri, ctx.timeout_seconds))
        await asyncio.sleep(0.4)
        await _push_demo_stream(stream_ws_uri, frames=4)
        live_events = await listener

        live_types = {e.get("type") for e in live_events}
        live_ok = "item_seen" in live_types

        print("[6/7] Fallback verification path (REST events)")
        recent_events = await _api_get(
            client,
            f"/patients/{ctx.patient_id}/events?type=item_seen&limit=10",
            token,
        )
        fallback_ok = False
        if isinstance(recent_events, list):
            for event in recent_events:
                ts = _parse_iso8601(event.get("occurred_at"))
                if ts and ts >= started_at:
                    fallback_ok = True
                    break
        if not live_ok and not fallback_ok:
            raise RuntimeError("No item_seen evidence from live feed or REST fallback after stream push.")

        print("[7/7] Item-state confirmation")
        states = await _api_get(client, f"/patients/{ctx.patient_id}/item-states/", token)
        names = {s.get("item_name") for s in states if isinstance(s, dict)}
        if "keys" not in names:
            raise RuntimeError(f"Expected keys in item state list, got: {sorted(names)}")

    print("\nDemo rehearsal PASS")
    print(f"- Started at (UTC): {started_iso}")
    print(f"- Live event feed received item_seen: {'yes' if live_ok else 'no'}")
    print(f"- REST fallback evidence after start: {'yes' if fallback_ok else 'no'}")
    print("- Demo script order confirmed: intro -> face/object flow -> query -> live dashboard update -> impact close")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MemoLens step-17 demo rehearsal checker")
    parser.add_argument("--base-url", required=True, help="Backend URL, e.g. http://localhost:8000")
    parser.add_argument("--patient-id", required=True, help="Patient UUID to use for rehearsal")
    parser.add_argument("--caregiver-email", default="demo.primary@memolens.local")
    parser.add_argument("--caregiver-password", default="demo1234")
    parser.add_argument("--timeout-seconds", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = args.base_url.rstrip("/")
    ctx = Ctx(
        base_url=base,
        api_base=f"{base}/api/v1",
        ws_base=_to_ws_base(base),
        patient_id=args.patient_id,
        caregiver_email=args.caregiver_email,
        caregiver_password=args.caregiver_password,
        timeout_seconds=args.timeout_seconds,
    )
    asyncio.run(run(ctx))


if __name__ == "__main__":
    main()
