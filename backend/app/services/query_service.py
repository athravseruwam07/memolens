"""
Memory query logic.
Parses a natural-language question and returns structured results from the database.
"""

from datetime import date, datetime, time, timezone
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import ItemState, Event, DailyNote, Reminder


MEDICATION_KEYWORDS = {"medication", "medicine", "pills", "pill", "meds"}


def _normalize(q: str) -> str:
    return q.strip().lower()


def _is_medication_adherence_question(q: str) -> bool:
    return (
        any(k in q for k in MEDICATION_KEYWORDS)
        and any(p in q for p in ["did i take", "have i taken", "took", "take my"])
    )


def _is_medication_general_question(q: str) -> bool:
    return any(k in q for k in MEDICATION_KEYWORDS)


def _start_of_today_utc(hour: int = 9, minute: int = 0) -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time(hour=hour, minute=minute), tzinfo=timezone.utc)


async def process_query(db: AsyncSession, patient_id: UUID, question: str) -> dict:
    q = _normalize(question)

    # Medication adherence: "Did I take my medication?"
    if _is_medication_adherence_question(q):
        cutoff = _start_of_today_utc(9, 0)
        med_item_seen = await db.execute(
            select(Event)
            .where(
                Event.patient_id == patient_id,
                Event.type == "item_seen",
                Event.occurred_at >= cutoff,
            )
            .order_by(desc(Event.occurred_at))
            .limit(50)
        )
        med_hits = []
        for event in med_item_seen.scalars().all():
            payload = event.payload or {}
            item_name = str(payload.get("item_name", "")).lower()
            if any(k in item_name for k in MEDICATION_KEYWORDS):
                med_hits.append(event)

        latest = med_hits[0] if med_hits else None
        taken = latest is not None
        return {
            "answer_type": "medication_adherence",
            "results": {
                "taken": taken,
                "checked_after": cutoff.isoformat(),
                "last_medication_item_seen_at": latest.occurred_at.isoformat() if latest else None,
                "evidence": latest.payload if latest else None,
                "message": (
                    "It looks like your medication was handled today."
                    if taken
                    else "I can't confirm medication was handled today after 9:00 AM."
                ),
            },
        }

    # Item lookup: keys, phone, wallet, etc.
    item_keywords = [
        "keys",
        "phone",
        "wallet",
        "computer mouse",
        "mouse",
        "laptop",
        "shoes",
        "glasses",
        "remote",
        "medication",
        "medicine",
        "pills",
    ]
    matched_items = [kw for kw in item_keywords if kw in q]

    if matched_items or "where" in q:
        result = await db.execute(
            select(ItemState).where(ItemState.patient_id == patient_id)
        )
        items = result.scalars().all()
        if matched_items:
            items = [i for i in items if any(kw in i.item_name.lower() for kw in matched_items)]
        return {
            "answer_type": "item_location",
            "results": [
                {
                    "item": i.item_name,
                    "room": i.last_seen_room,
                    "last_seen_at": i.last_seen_at.isoformat() if i.last_seen_at else None,
                    "confidence": i.confidence,
                }
                for i in items
            ],
        }

    # Person lookup
    if any(kw in q for kw in ["who", "person", "this"]):
        result = await db.execute(
            select(Event)
            .where(Event.patient_id == patient_id, Event.type == "face_recognized")
            .order_by(desc(Event.occurred_at))
            .limit(1)
        )
        event = result.scalar_one_or_none()
        return {
            "answer_type": "person_recognized",
            "results": event.payload if event else None,
        }

    # Medication lookup (general)
    if _is_medication_general_question(q):
        item_result = await db.execute(
            select(ItemState).where(
                ItemState.patient_id == patient_id,
                ItemState.item_name.ilike("%medication%"),
            )
        )
        items = item_result.scalars().all()
        reminder_result = await db.execute(
            select(Reminder).where(
                Reminder.patient_id == patient_id,
                Reminder.active == True,
            )
        )
        reminders = reminder_result.scalars().all()
        med_reminders = [r for r in reminders if "med" in (r.message or "").lower() or "pill" in (r.message or "").lower()]
        return {
            "answer_type": "medication",
            "results": {
                "item_states": [
                    {"item": i.item_name, "room": i.last_seen_room, "last_seen_at": i.last_seen_at.isoformat() if i.last_seen_at else None}
                    for i in items
                ],
                "reminders": [{"message": r.message, "trigger": r.trigger_meta} for r in med_reminders],
            },
        }

    # Daily schedule / notes
    if any(kw in q for kw in ["today", "remember", "schedule"]):
        today = date.today()
        notes_result = await db.execute(
            select(DailyNote).where(
                DailyNote.patient_id == patient_id,
                DailyNote.note_date == today,
            )
        )
        notes = notes_result.scalars().all()
        reminder_result = await db.execute(
            select(Reminder).where(
                Reminder.patient_id == patient_id,
                Reminder.active == True,
            )
        )
        reminders = reminder_result.scalars().all()
        return {
            "answer_type": "daily_summary",
            "results": {
                "notes": [{"content": n.content, "date": n.note_date.isoformat()} for n in notes],
                "reminders": [{"message": r.message, "type": r.type, "trigger": r.trigger_meta} for r in reminders],
            },
        }

    # Fallback
    return {
        "answer_type": "unknown",
        "results": "Sorry, I couldn't understand the question. Try asking about a person, item, or your schedule.",
    }
