"""
Memory query logic.
Parses a natural-language question and returns structured results from the database.
"""

from datetime import date
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import ItemState, Event, DailyNote, Reminder


async def process_query(db: AsyncSession, patient_id: UUID, question: str) -> dict:
    q = question.lower()

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

    # Medication check
    if any(kw in q for kw in ["medication", "medicine", "pills"]):
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
