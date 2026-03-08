import base64
import asyncio
import json
from contextlib import suppress
from uuid import UUID
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.database import async_session
from app.models.db import FamiliarPerson, ItemState, Event, Patient, User, PatientCaregiver
from app.services.face_service import generate_face_embedding, match_face_against_known
from app.services.object_service import (
    detect_items_from_frame,
    extract_item_detections,
    merge_detections,
    resolve_item_room,
    should_write_item_update,
)
from app.services.reminder_service import get_triggered_reminders
from app.services.storage_service import StorageError, upload_item_snapshot

router = APIRouter()
STREAM_RUNTIME_REFRESH_SECONDS = 5.0
_viewers_by_patient: dict[str, set[WebSocket]] = {}
_viewers_lock = asyncio.Lock()


def _parse_stream_payload(raw_data: str) -> tuple[bytes, dict[str, Any], str]:
    # Backward compatible: raw base64 string OR JSON envelope.
    payload: dict[str, Any] = {}
    frame_b64 = raw_data

    try:
        parsed = json.loads(raw_data)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        payload = parsed
        frame_b64 = (
            parsed.get("frame_b64")
            or parsed.get("frame")
            or parsed.get("image_b64")
            or ""
        )

    frame_bytes = base64.b64decode(frame_b64)
    return frame_bytes, payload, frame_b64


def _serialize_event(event: Event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "patient_id": str(event.patient_id),
        "type": event.type,
        "payload": event.payload,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
    }


def _decode_token_subject(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    return payload.get("sub")


def _build_known_list(people: list[FamiliarPerson]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "relationship": p.relationship,
            "notes": p.notes,
            "conversation_prompt": p.conversation_prompt,
            "face_embeddings": p.face_embeddings or [],
        }
        for p in people
    ]


async def _load_stream_runtime(patient_id: UUID) -> tuple[list[str], list[dict[str, Any]]] | None:
    async with async_session() as db:
        patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = patient_result.scalar_one_or_none()
        if not patient:
            return None

        people_result = await db.execute(
            select(FamiliarPerson).where(FamiliarPerson.patient_id == patient_id)
        )
        people = people_result.scalars().all()
        return list(patient.tracked_items or []), _build_known_list(people)


async def _send_json_locked(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    payload: dict[str, Any],
) -> None:
    async with send_lock:
        await websocket.send_json(payload)


async def _log_face_recognized_event(
    patient_id: UUID,
    person_id: str,
    name: str,
) -> None:
    async with async_session() as db:
        db.add(
            Event(
                patient_id=patient_id,
                type="face_recognized",
                payload={"person_id": person_id, "name": name},
            )
        )
        await db.commit()


async def _process_items_pipeline(
    *,
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    patient_id: UUID,
    tracked_items: list[str],
    frame_bytes: bytes,
    payload: dict[str, Any],
    matched_person_id: str | None,
) -> None:
    try:
        payload_detections = extract_item_detections(payload=payload, tracked_items=tracked_items)
        cv_detections = await asyncio.to_thread(detect_items_from_frame, frame_bytes, tracked_items)
        item_detections = merge_detections(payload_detections, cv_detections)

        current_room = payload.get("room") or payload.get("room_label") or payload.get("location")
        near_exit = bool(payload.get("near_exit", False))
        detected_items = {det["item_name"] for det in item_detections if det.get("item_name")}

        responses: list[dict[str, Any]] = []
        has_writes = False

        async with async_session() as db:
            states_by_name: dict[str, ItemState] = {}
            item_names = [det["item_name"] for det in item_detections if det.get("item_name")]
            if item_names:
                states_result = await db.execute(
                    select(ItemState).where(
                        ItemState.patient_id == patient_id,
                        ItemState.item_name.in_(item_names),
                    )
                )
                states = states_result.scalars().all()
                states_by_name = {s.item_name: s for s in states}

            for det in item_detections:
                item_name = det.get("item_name")
                if not item_name:
                    continue

                resolved_room = resolve_item_room(det, payload)
                confidence = det.get("confidence")
                if isinstance(confidence, (int, float)):
                    confidence = float(confidence)
                else:
                    confidence = None

                state = states_by_name.get(item_name)
                now = datetime.utcnow()
                if not should_write_item_update(
                    state,
                    resolved_room=resolved_room,
                    confidence=confidence,
                    now=now,
                ):
                    continue

                try:
                    snapshot_url = await upload_item_snapshot(
                        patient_id=str(patient_id),
                        item_name=item_name,
                        content=frame_bytes,
                    )
                except StorageError as exc:
                    responses.append({"error": str(exc)})
                    continue

                if state:
                    state.last_seen_room = resolved_room
                    state.last_seen_at = now
                    state.snapshot_url = snapshot_url
                    state.confidence = confidence
                else:
                    state = ItemState(
                        patient_id=patient_id,
                        item_name=item_name,
                        last_seen_room=resolved_room,
                        last_seen_at=now,
                        snapshot_url=snapshot_url,
                        confidence=confidence,
                    )
                    db.add(state)
                    states_by_name[item_name] = state

                db.add(
                    Event(
                        patient_id=patient_id,
                        type="item_seen",
                        payload={
                            "item_name": item_name,
                            "room": resolved_room,
                            "confidence": confidence,
                            "snapshot_url": snapshot_url,
                        },
                    )
                )
                has_writes = True
                responses.append(
                    {
                        "type": "item",
                        "item_name": item_name,
                        "room": resolved_room,
                        "confidence": confidence,
                    }
                )

            triggered = await get_triggered_reminders(
                db,
                patient_id,
                person_id=matched_person_id,
                current_room=current_room,
                detected_items=detected_items,
                near_exit=near_exit,
            )
            for reminder in triggered:
                responses.append({"type": "reminder", "message": reminder.message})
                db.add(
                    Event(
                        patient_id=patient_id,
                        type="reminder_triggered",
                        payload={
                            "reminder_id": str(reminder.id),
                            "message": reminder.message,
                            "trigger_type": reminder.type,
                        },
                    )
                )
                has_writes = True

            if has_writes:
                await db.commit()

        for resp in responses:
            await _send_json_locked(websocket, send_lock, resp)
    except Exception:
        return


async def _register_viewer(patient_id: UUID, websocket: WebSocket) -> None:
    key = str(patient_id)
    async with _viewers_lock:
        viewers = _viewers_by_patient.setdefault(key, set())
        viewers.add(websocket)


async def _unregister_viewer(patient_id: UUID, websocket: WebSocket) -> None:
    key = str(patient_id)
    async with _viewers_lock:
        viewers = _viewers_by_patient.get(key)
        if not viewers:
            return
        viewers.discard(websocket)
        if not viewers:
            _viewers_by_patient.pop(key, None)


async def _broadcast_frame_to_viewers(patient_id: UUID, frame_b64: str) -> None:
    key = str(patient_id)
    async with _viewers_lock:
        viewers = list(_viewers_by_patient.get(key, set()))
    if not viewers:
        return

    stale: list[WebSocket] = []
    payload = {"type": "frame", "frame_b64": frame_b64}
    for viewer in viewers:
        try:
            await viewer.send_json(payload)
        except Exception:
            stale.append(viewer)

    if stale:
        async with _viewers_lock:
            current = _viewers_by_patient.get(key)
            if current is None:
                return
            for viewer in stale:
                current.discard(viewer)
            if not current:
                _viewers_by_patient.pop(key, None)


@router.websocket("/ws/stream/{patient_id}")
async def websocket_stream(websocket: WebSocket, patient_id: UUID):
    await websocket.accept()
    send_lock = asyncio.Lock()
    loop = asyncio.get_running_loop()
    runtime_last_loaded_at = 0.0
    tracked_items_cache: list[str] = []
    known_people_cache: list[dict[str, Any]] = []
    item_task: asyncio.Task | None = None
    broadcast_task: asyncio.Task | None = None

    try:
        while True:
            data = await websocket.receive_text()

            try:
                frame_bytes, payload, frame_b64 = _parse_stream_payload(data)
            except Exception:
                await _send_json_locked(websocket, send_lock, {"error": "Invalid stream payload"})
                continue
            if not frame_bytes:
                await _send_json_locked(websocket, send_lock, {"error": "Empty frame payload"})
                continue

            if broadcast_task is None or broadcast_task.done():
                broadcast_task = asyncio.create_task(
                    _broadcast_frame_to_viewers(patient_id, frame_b64)
                )

            now_ts = loop.time()
            if (
                now_ts - runtime_last_loaded_at >= STREAM_RUNTIME_REFRESH_SECONDS
                or not known_people_cache
            ):
                runtime = await _load_stream_runtime(patient_id)
                if runtime is None:
                    await _send_json_locked(websocket, send_lock, {"error": "Patient not found"})
                    continue
                tracked_items_cache, known_people_cache = runtime
                runtime_last_loaded_at = now_ts

            frame_embedding = await asyncio.to_thread(generate_face_embedding, frame_bytes)
            matched = match_face_against_known(frame_embedding, known_people_cache)

            if matched:
                print(f"{matched['name']} person detected")
                await _send_json_locked(
                    websocket,
                    send_lock,
                    {
                        "type": "person",
                        "name": matched["name"],
                        "relationship": matched.get("relationship"),
                        "notes": matched.get("notes"),
                        "conversation_prompt": matched.get("conversation_prompt"),
                    },
                )
                asyncio.create_task(
                    _log_face_recognized_event(
                        patient_id=patient_id,
                        person_id=matched["id"],
                        name=matched["name"],
                    )
                )
            else:
                print("person not detected")
                await _send_json_locked(websocket, send_lock, {"type": "no_match"})

            if item_task is None or item_task.done():
                item_task = asyncio.create_task(
                    _process_items_pipeline(
                        websocket=websocket,
                        send_lock=send_lock,
                        patient_id=patient_id,
                        tracked_items=list(tracked_items_cache),
                        frame_bytes=frame_bytes,
                        payload=payload,
                        matched_person_id=matched.get("id") if matched else None,
                    )
                )

    except WebSocketDisconnect:
        if broadcast_task and not broadcast_task.done():
            broadcast_task.cancel()
            with suppress(asyncio.CancelledError):
                await broadcast_task
        if item_task and not item_task.done():
            item_task.cancel()
            with suppress(asyncio.CancelledError):
                await item_task
        return


@router.websocket("/ws/view/{patient_id}")
async def websocket_view(websocket: WebSocket, patient_id: UUID):
    # Temporary bypass for live video debugging:
    # this viewer endpoint intentionally skips auth.

    await websocket.accept()
    await _register_viewer(patient_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _unregister_viewer(patient_id, websocket)


@router.websocket("/ws/events/{patient_id}")
async def websocket_events(websocket: WebSocket, patient_id: UUID):
    token = websocket.query_params.get("token", "")
    user_sub = _decode_token_subject(token)
    if not user_sub:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    try:
        user_id = UUID(user_sub)
    except ValueError:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        link_result = await db.execute(
            select(PatientCaregiver).where(
                PatientCaregiver.patient_id == patient_id,
                PatientCaregiver.caregiver_id == user.id,
            )
        )
        if not link_result.scalar_one_or_none():
            await websocket.close(code=1008, reason="Patient access denied")
            return

    await websocket.accept()
    seen_ids: set[str] = set()

    try:
        while True:
            async with async_session() as db:
                result = await db.execute(
                    select(Event)
                    .where(Event.patient_id == patient_id)
                    .order_by(Event.occurred_at.desc())
                    .limit(30)
                )
                latest = list(reversed(result.scalars().all()))

            for event in latest:
                event_id = str(event.id)
                if event_id in seen_ids:
                    continue
                await websocket.send_json({"type": "event", "event": _serialize_event(event)})
                seen_ids.add(event_id)

            if len(seen_ids) > 500:
                seen_ids = set(list(seen_ids)[-300:])

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        return
