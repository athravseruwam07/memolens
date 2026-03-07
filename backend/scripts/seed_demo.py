from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.db import DailyNote, Event, FamiliarPerson, ItemState, Patient, PatientCaregiver, Reminder, User
from app.services.auth_service import hash_password


PRIMARY_EMAIL = "demo.primary@memolens.local"
SECONDARY_EMAIL = "demo.secondary@memolens.local"
PASSWORD = "demo1234"


async def _get_or_create_user(db: AsyncSession, *, email: str, name: str, role: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        email=email,
        name=name,
        role=role,
        hashed_password=hash_password(PASSWORD),
    )
    db.add(user)
    await db.flush()
    return user


async def _get_or_create_patient(db: AsyncSession, *, name: str, primary_caregiver_id) -> Patient:
    result = await db.execute(select(Patient).where(Patient.name == name))
    patient = result.scalar_one_or_none()
    if patient:
        return patient

    patient = Patient(
        name=name,
        age=78,
        primary_caregiver=primary_caregiver_id,
        emergency_contact={"name": "Sarah", "phone": "+1-555-555-0100"},
        tracked_items=["keys", "phone", "wallet", "medication"],
        common_issues="Occasional confusion around appointments and item placement.",
    )
    db.add(patient)
    await db.flush()
    return patient


async def _ensure_caregiver_link(db: AsyncSession, *, patient_id, caregiver_id, role: str) -> None:
    result = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == caregiver_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        return
    db.add(
        PatientCaregiver(
            patient_id=patient_id,
            caregiver_id=caregiver_id,
            role=role,
        )
    )


async def _seed_people(db: AsyncSession, *, patient_id, created_by) -> None:
    demos = [
        {
            "name": "Sarah",
            "relationship": "daughter",
            "notes": "Visits for lunch most Tuesdays.",
            "conversation_prompt": "Ask Sarah about her kids.",
            "importance_level": 5,
        },
        {
            "name": "Dr. Patel",
            "relationship": "doctor",
            "notes": "Family physician.",
            "conversation_prompt": "You have a checkup next week.",
            "importance_level": 4,
        },
    ]

    for person_data in demos:
        result = await db.execute(
            select(FamiliarPerson).where(
                FamiliarPerson.patient_id == patient_id,
                FamiliarPerson.name == person_data["name"],
            )
        )
        if result.scalar_one_or_none():
            continue

        db.add(
            FamiliarPerson(
                id=uuid4(),
                patient_id=patient_id,
                photos=[],
                face_embeddings=[],
                created_by=created_by,
                **person_data,
            )
        )


async def _seed_items(db: AsyncSession, *, patient_id) -> None:
    now = datetime.now(timezone.utc)
    demos = [
        ("keys", "kitchen", 0.94),
        ("phone", "living room", 0.90),
        ("wallet", "bedroom", 0.82),
    ]
    for item_name, room, confidence in demos:
        result = await db.execute(
            select(ItemState).where(
                ItemState.patient_id == patient_id,
                ItemState.item_name == item_name,
            )
        )
        state = result.scalar_one_or_none()
        if state:
            state.last_seen_room = room
            state.last_seen_at = now
            state.confidence = confidence
            continue

        db.add(
            ItemState(
                patient_id=patient_id,
                item_name=item_name,
                last_seen_room=room,
                last_seen_at=now,
                snapshot_url=None,
                confidence=confidence,
            )
        )


async def _seed_reminders(db: AsyncSession, *, patient_id, created_by) -> None:
    now_hhmm = datetime.now(timezone.utc).strftime("%H:%M")
    demos = [
        ("time", {"time": now_hhmm, "cooldown_seconds": 60}, "Take your medication now."),
        ("person", {"person_id": "demo-sarah", "cooldown_seconds": 300}, "This is Sarah, your daughter."),
        ("location", {"room": "kitchen", "cooldown_seconds": 300}, "You are in the kitchen. Have some water."),
        ("object", {"item": "keys", "mode": "missing_before_exit", "cooldown_seconds": 300}, "Remember your keys before leaving."),
    ]

    for rtype, trigger_meta, message in demos:
        result = await db.execute(
            select(Reminder).where(
                Reminder.patient_id == patient_id,
                Reminder.type == rtype,
                Reminder.message == message,
            )
        )
        if result.scalar_one_or_none():
            continue

        db.add(
            Reminder(
                patient_id=patient_id,
                type=rtype,
                trigger_meta=trigger_meta,
                message=message,
                active=True,
                created_by=created_by,
            )
        )


async def _seed_notes_and_events(db: AsyncSession, *, patient_id, created_by) -> None:
    today = date.today()
    note_text = "Sarah is visiting for lunch at noon."

    note_result = await db.execute(
        select(DailyNote).where(
            DailyNote.patient_id == patient_id,
            DailyNote.note_date == today,
            DailyNote.content == note_text,
        )
    )
    if not note_result.scalar_one_or_none():
        db.add(
            DailyNote(
                patient_id=patient_id,
                note_date=today,
                content=note_text,
                created_by=created_by,
            )
        )

    event_defs = [
        ("item_seen", {"item_name": "keys", "room": "kitchen", "confidence": 0.94}),
        ("face_recognized", {"person_id": "demo-sarah", "name": "Sarah"}),
        ("reminder_triggered", {"reminder": "Take your medication now."}),
    ]
    for etype, payload in event_defs:
        event_result = await db.execute(
            select(Event).where(
                Event.patient_id == patient_id,
                Event.type == etype,
                Event.payload == payload,
            )
        )
        if event_result.scalar_one_or_none():
            continue
        db.add(Event(patient_id=patient_id, type=etype, payload=payload))


async def seed() -> None:
    async with async_session() as db:
        primary = await _get_or_create_user(
            db,
            email=PRIMARY_EMAIL,
            name="Primary Caregiver",
            role="caregiver",
        )
        secondary = await _get_or_create_user(
            db,
            email=SECONDARY_EMAIL,
            name="Secondary Caregiver",
            role="caregiver",
        )

        patient = await _get_or_create_patient(
            db,
            name="John Memory",
            primary_caregiver_id=primary.id,
        )

        await _ensure_caregiver_link(db, patient_id=patient.id, caregiver_id=primary.id, role="PRIMARY")
        await _ensure_caregiver_link(db, patient_id=patient.id, caregiver_id=secondary.id, role="SECONDARY")

        await _seed_people(db, patient_id=patient.id, created_by=primary.id)
        await _seed_items(db, patient_id=patient.id)
        await _seed_reminders(db, patient_id=patient.id, created_by=primary.id)
        await _seed_notes_and_events(db, patient_id=patient.id, created_by=primary.id)

        await db.commit()

        print("Seed complete")
        print(f"Primary caregiver: {PRIMARY_EMAIL} / {PASSWORD}")
        print(f"Secondary caregiver: {SECONDARY_EMAIL} / {PASSWORD}")
        print(f"Patient ID: {patient.id}")


if __name__ == "__main__":
    asyncio.run(seed())
