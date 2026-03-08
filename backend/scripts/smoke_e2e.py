from __future__ import annotations

import argparse
import asyncio
import base64
import json
import secrets
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
class SmokeContext:
    base_url: str
    api_base: str
    ws_base: str
    timeout_seconds: int


def _normalize_base(base_url: str) -> str:
    return base_url.rstrip("/")


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
        raise RuntimeError(f"API error for POST {path}: {payload['error']}")
    return payload["data"]


async def _api_get(client: httpx.AsyncClient, path: str, token: str) -> dict[str, Any] | list[Any]:
    res = await client.get(path, headers={"Authorization": f"Bearer {token}"})
    res.raise_for_status()
    payload = res.json()
    if payload.get("error"):
        raise RuntimeError(f"API error for GET {path}: {payload['error']}")
    return payload["data"]


async def _collect_event_messages(uri: str, required_types: set[str], timeout_seconds: int) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    deadline = asyncio.get_running_loop().time() + timeout_seconds

    async with websockets.connect(uri, max_size=10_000_000) as ws:
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.1, deadline - asyncio.get_running_loop().time())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break

            msg = json.loads(raw)
            if msg.get("type") != "event":
                continue
            event = msg.get("event") or {}
            messages.append(event)
            got_types = {e.get("type") for e in messages}
            if required_types.issubset(got_types):
                break

    return messages


async def _send_stream_frames(uri: str, frames: int = 3, delay: float = 0.35) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    async with websockets.connect(uri, max_size=10_000_000) as ws:
        for _ in range(frames):
            payload = {
                "frame_b64": JPEG_1X1_BASE64,
                "room": "kitchen",
                "near_exit": False,
                "detections": [
                    {"item": "medication", "room": "kitchen", "confidence": 0.97},
                    {"item": "keys", "room": "kitchen", "confidence": 0.88},
                ],
            }
            await ws.send(json.dumps(payload))

            # Collect any immediate messages for this frame window.
            for _ in range(4):
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.25)
                except asyncio.TimeoutError:
                    break
                try:
                    responses.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue

            await asyncio.sleep(delay)

    return responses


async def run_smoke(ctx: SmokeContext) -> None:
    email = f"smoke.{secrets.token_hex(4)}@memolens.local"
    password = "SmokePass123!"

    async with httpx.AsyncClient(base_url=ctx.api_base, timeout=20.0) as client:
        print("[1/8] Register caregiver...")
        auth = await _api_post(
            client,
            "/auth/register",
            {
                "email": email,
                "password": password,
                "name": "Smoke Tester",
                "role": "caregiver",
            },
        )
        if not auth.get("token"):
            raise RuntimeError("Register succeeded but no token returned")

        print("[2/8] Login caregiver...")
        login = await _api_post(
            client,
            "/auth/login",
            {
                "email": email,
                "password": password,
            },
        )
        token = login.get("token")
        if not token:
            raise RuntimeError("Login failed: no token returned")

        print("[3/8] Create patient...")
        patient = await _api_post(
            client,
            "/patients/",
            {
                "name": "Smoke Patient",
                "age": 76,
                "tracked_items": ["keys", "medication", "phone"],
                "common_issues": "Smoke test profile",
            },
            token,
        )
        patient_id = patient["id"]

        print("[4/8] Add daily note (for note-based reminder trigger)...")
        _ = await _api_post(
            client,
            f"/patients/{patient_id}/daily-notes/",
            {"content": f"Smoke note reminder {datetime.now(timezone.utc).isoformat()}"},
            token,
        )

        events_ws_uri = f"{ctx.ws_base}/ws/events/{patient_id}?token={token}"
        stream_ws_uri = f"{ctx.ws_base}/ws/stream/{patient_id}"

        print("[5/8] Start live event listener + send Pi stream frames...")
        required_types = {"item_seen", "reminder_triggered"}
        listener_task = asyncio.create_task(
            _collect_event_messages(events_ws_uri, required_types, ctx.timeout_seconds)
        )
        await asyncio.sleep(0.5)
        stream_responses = await _send_stream_frames(stream_ws_uri, frames=4)
        event_messages = await listener_task

        got_types = {e.get("type") for e in event_messages}
        if not required_types.issubset(got_types):
            raise RuntimeError(
                f"Missing expected live events. got={sorted(got_types)} expected={sorted(required_types)}"
            )

        print("[6/8] Verify item state updated...")
        items = await _api_get(client, f"/patients/{patient_id}/item-states/", token)
        item_names = {i.get("item_name") for i in items if isinstance(i, dict)}
        if "medication" not in item_names and "keys" not in item_names:
            raise RuntimeError(f"Item states not updated as expected: {sorted(item_names)}")

        print("[7/8] Verify query endpoint answers medication adherence...")
        query = await _api_post(
            client,
            "/query",
            {"patient_id": patient_id, "question": "Did I take my medication?"},
            token,
        )
        if query.get("answer_type") != "medication_adherence":
            raise RuntimeError(f"Unexpected answer_type from /query: {query.get('answer_type')}")

        print("[8/8] Verify stream emitted patient-facing updates...")
        stream_types = {m.get("type") for m in stream_responses if isinstance(m, dict)}
        if "reminder" not in stream_types and "item" not in stream_types:
            raise RuntimeError(f"Unexpected stream responses: {stream_types}")

    print("\nSmoke test PASSED")
    print(f"- API base: {ctx.api_base}")
    print(f"- WebSocket base: {ctx.ws_base}")
    print(f"- Created patient: {patient_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MemoLens deployed E2E smoke test")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Backend base URL, e.g. https://memolens-backend.onrender.com",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=25,
        help="Max seconds to wait for live event types",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = _normalize_base(args.base_url)
    ctx = SmokeContext(
        base_url=base,
        api_base=f"{base}/api/v1",
        ws_base=_to_ws_base(base),
        timeout_seconds=args.timeout_seconds,
    )
    asyncio.run(run_smoke(ctx))


if __name__ == "__main__":
    main()
