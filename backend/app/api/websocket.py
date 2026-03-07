import base64
import json
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session
from app.models.db import FamiliarPerson, ItemState, Event
from app.services.face_service import generate_face_embedding, match_face_against_known
from app.services.reminder_service import get_triggered_time_reminders

router = APIRouter()


@router.websocket("/ws/stream/{patient_id}")
async def websocket_stream(websocket: WebSocket, patient_id: UUID):
    await websocket.accept()
    print(f"[WS] Pi connected for patient {patient_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WS] Received frame for patient {patient_id} ({len(data)} bytes)")

            try:
                frame_bytes = base64.b64decode(data)
            except Exception:
                await websocket.send_json({"error": "Invalid base64 frame"})
                continue

            async with async_session() as db:
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

                # Check for time-based reminders
                triggered = await get_triggered_time_reminders(db, patient_id)
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
                        payload={"reminder_id": str(r.id), "message": r.message},
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
