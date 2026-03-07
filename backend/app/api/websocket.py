import base64
import asyncio
import json
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
from app.services.object_service import detect_items_from_frame, extract_item_detections, merge_detections
from app.services.reminder_service import get_triggered_reminders
from app.services.storage_service import upload_item_snapshot

router = APIRouter()


def _parse_stream_payload(raw_data: str) -> tuple[bytes, dict[str, Any]]:
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
    return frame_bytes, payload


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


@router.websocket("/ws/stream/{patient_id}")
async def websocket_stream(websocket: WebSocket, patient_id: UUID):
    await websocket.accept()
    print(f"[WS] Pi connected for patient {patient_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WS] Received frame for patient {patient_id} ({len(data)} bytes)")

            try:
                frame_bytes, payload = _parse_stream_payload(data)
            except Exception:
                await websocket.send_json({"error": "Invalid stream payload"})
                continue
            if not frame_bytes:
                await websocket.send_json({"error": "Empty frame payload"})
                continue

            async with async_session() as db:
                patient_result = await db.execute(
                    select(Patient).where(Patient.id == patient_id)
                )
                patient = patient_result.scalar_one_or_none()
                if not patient:
                    await websocket.send_json({"error": "Patient not found"})
                    continue

                # Generate embedding from frame
                frame_embedding = generate_face_embedding(frame_bytes)

                # Load known people for this patient
                result = await db.execute(
                    select(FamiliarPerson).where(FamiliarPerson.patient_id == patient_id)
                )
                people = result.scalars().all()

                known_list = [
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

                matched = match_face_against_known(frame_embedding, known_list)

                responses = []

                if matched:
                    print(f"[WS] Face recognized: {matched['name']} for patient {patient_id}")
                    face_result = {
                        "type": "person",
                        "name": matched["name"],
                        "relationship": matched.get("relationship"),
                        "notes": matched.get("notes"),
                        "conversation_prompt": matched.get("conversation_prompt"),
                    }
                    responses.append(face_result)

                    # Log event
                    event = Event(
                        patient_id=patient_id,
                        type="face_recognized",
                        payload={"person_id": matched["id"], "name": matched["name"]},
                    )
                    db.add(event)

                # Process item detections from Pi payload and keep latest item state.
                tracked_items = patient.tracked_items or []
                payload_detections = extract_item_detections(payload=payload, tracked_items=tracked_items)
                cv_detections = detect_items_from_frame(frame_bytes=frame_bytes, tracked_items=tracked_items)
                item_detections = merge_detections(payload_detections, cv_detections)
                for det in item_detections:
                    snapshot_url = await upload_item_snapshot(
                        patient_id=str(patient_id),
                        item_name=det["item_name"],
                        content=frame_bytes,
                    )
                    state_result = await db.execute(
                        select(ItemState).where(
                            ItemState.patient_id == patient_id,
                            ItemState.item_name == det["item_name"],
                        )
                    )
                    state = state_result.scalar_one_or_none()
                    if state:
                        state.last_seen_room = det.get("room")
                        state.last_seen_at = datetime.utcnow()
                        state.snapshot_url = snapshot_url
                        state.confidence = det.get("confidence")
                    else:
                        state = ItemState(
                            patient_id=patient_id,
                            item_name=det["item_name"],
                            last_seen_room=det.get("room"),
                            last_seen_at=datetime.utcnow(),
                            snapshot_url=snapshot_url,
                            confidence=det.get("confidence"),
                        )
                        db.add(state)

                    db.add(
                        Event(
                            patient_id=patient_id,
                            type="item_seen",
                            payload={
                                "item_name": det["item_name"],
                                "room": det.get("room"),
                                "confidence": det.get("confidence"),
                                "snapshot_url": snapshot_url,
                            },
                        )
                    )
                    responses.append(
                        {
                            "type": "item",
                            "item_name": det["item_name"],
                            "room": det.get("room"),
                            "confidence": det.get("confidence"),
                        }
                    )

                current_room = payload.get("room") or payload.get("room_label") or payload.get("location")
                near_exit = bool(payload.get("near_exit", False))
                detected_items = {det["item_name"] for det in item_detections}

                triggered = await get_triggered_reminders(
                    db,
                    patient_id,
                    person_id=matched.get("id") if matched else None,
                    current_room=current_room,
                    detected_items=detected_items,
                    near_exit=near_exit,
                )
                for r in triggered:
                    print(f"[WS] Reminder triggered: {r.message} for patient {patient_id}")
                    responses.append({
                        "type": "reminder",
                        "message": r.message,
                    })
                    # Log event
                    event = Event(
                        patient_id=patient_id,
                        type="reminder_triggered",
                        payload={
                            "reminder_id": str(r.id),
                            "message": r.message,
                            "trigger_type": r.type,
                        },
                    )
                    db.add(event)

                await db.commit()

                if responses:
                    for resp in responses:
                        await websocket.send_json(resp)
                else:
                    await websocket.send_json({"type": "no_match"})

    except WebSocketDisconnect:
        print(f"[WS] Pi disconnected for patient {patient_id}")


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
