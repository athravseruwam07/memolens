"""
Reminder trigger logic.
Checks active reminders against current context and returns triggered ones.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.db import DailyNote, Event, Reminder


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _meta(reminder: Reminder) -> dict[str, Any]:
    return reminder.trigger_meta or {}


def _match_time(reminder: Reminder, now_hhmm: str) -> bool:
    meta = _meta(reminder)
    return _normalize_text(meta.get("time")) == _normalize_text(now_hhmm)


def _match_person(reminder: Reminder, person_id: str | None) -> bool:
    if not person_id:
        return False
    meta = _meta(reminder)
    return _normalize_text(meta.get("person_id")) == _normalize_text(person_id)


def _match_location(reminder: Reminder, current_room: str | None) -> bool:
    if not current_room:
        return False
    room = _normalize_text(current_room)
    meta = _meta(reminder)
    one_room = _normalize_text(meta.get("room"))
    many_rooms = meta.get("rooms")
    if one_room and one_room == room:
        return True
    if isinstance(many_rooms, list):
        return room in {_normalize_text(r) for r in many_rooms}
    return False


def _match_object(reminder: Reminder, detected_items: set[str], near_exit: bool) -> bool:
    meta = _meta(reminder)
    mode = _normalize_text(meta.get("mode") or meta.get("trigger"))
    one_item = _normalize_text(meta.get("item"))
    many_items = meta.get("items")
    items: set[str] = set()
    if one_item:
        items.add(one_item)
    if isinstance(many_items, list):
        items.update({_normalize_text(i) for i in many_items if _normalize_text(i)})
    if not items:
        return False

    if mode == "missing_before_exit":
        return near_exit and any(item not in detected_items for item in items)
    return any(item in detected_items for item in items)


def _type_matches(
    reminder: Reminder,
    *,
    now_hhmm: str,
    person_id: str | None,
    current_room: str | None,
    detected_items: set[str],
    near_exit: bool,
) -> bool:
    reminder_type = _normalize_text(reminder.type)
    if reminder_type == "time":
        return _match_time(reminder, now_hhmm)
    if reminder_type == "person":
        return _match_person(reminder, person_id)
    if reminder_type == "location":
        return _match_location(reminder, current_room)
    if reminder_type == "object":
        return _match_object(reminder, detected_items, near_exit)
    return False


async def _was_recently_triggered(
    db: AsyncSession,
    patient_id: UUID,
    reminder_id: UUID,
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
    result = await db.execute(
        select(Event)
        .where(
            Event.patient_id == patient_id,
            Event.type == "reminder_triggered",
            Event.occurred_at >= cutoff,
        )
        .order_by(desc(Event.occurred_at))
        .limit(200)
    )
    for event in result.scalars().all():
        payload = event.payload or {}
        if _normalize_text(payload.get("reminder_id")) == _normalize_text(reminder_id):
            return True
    return False


async def _was_note_recently_triggered(
    db: AsyncSession,
    patient_id: UUID,
    note_id: UUID,
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
    result = await db.execute(
        select(Event)
        .where(
            Event.patient_id == patient_id,
            Event.type == "reminder_triggered",
            Event.occurred_at >= cutoff,
        )
        .order_by(desc(Event.occurred_at))
        .limit(200)
    )
    for event in result.scalars().all():
        payload = event.payload or {}
        if (
            _normalize_text(payload.get("trigger_type")) == "note"
            and _normalize_text(payload.get("note_id")) == _normalize_text(note_id)
        ):
            return True
    return False


async def get_triggered_reminders(
    db: AsyncSession,
    patient_id: UUID,
    *,
    person_id: str | None = None,
    current_room: str | None = None,
    detected_items: set[str] | None = None,
    near_exit: bool = False,
) -> list[Reminder]:
    """
    Return reminders triggered by current context.
    Supports time/person/location/object reminders.
    """
    now_hhmm = datetime.now(timezone.utc).strftime("%H:%M")
    detected_items = {_normalize_text(i) for i in (detected_items or set()) if _normalize_text(i)}

    result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active.is_(True),
        )
    )
    reminders = result.scalars().all()

    triggered: list[Reminder] = []
    for reminder in reminders:
        if not _type_matches(
            reminder,
            now_hhmm=now_hhmm,
            person_id=person_id,
            current_room=current_room,
            detected_items=detected_items,
            near_exit=near_exit,
        ):
            continue

        default_cooldown = 60 if _normalize_text(reminder.type) == "time" else 300
        cooldown_seconds = _parse_int(_meta(reminder).get("cooldown_seconds"), default_cooldown)
        if await _was_recently_triggered(db, patient_id, reminder.id, cooldown_seconds):
            continue

        triggered.append(reminder)

    return triggered


async def get_triggered_daily_note_reminders(
    db: AsyncSession,
    patient_id: UUID,
    *,
    cooldown_seconds: int = 1800,
) -> list[DailyNote]:
    """
    Return today's daily notes that have not recently been surfaced as reminders.
    """
    result = await db.execute(
        select(DailyNote).where(
            DailyNote.patient_id == patient_id,
            DailyNote.note_date == date.today(),
        )
    )
    notes = result.scalars().all()
    triggered: list[DailyNote] = []

    for note in notes:
        if await _was_note_recently_triggered(db, patient_id, note.id, cooldown_seconds):
            continue
        triggered.append(note)

    return triggered


async def get_triggered_time_reminders(db: AsyncSession, patient_id: UUID) -> list[Reminder]:
    """Get time-based reminders that should fire now (matching current HH:MM)."""
    return await get_triggered_reminders(db, patient_id)


async def get_person_reminders(db: AsyncSession, patient_id: UUID, person_id: str) -> list[Reminder]:
    """Get reminders triggered by recognizing a specific person."""
    return await get_triggered_reminders(db, patient_id, person_id=person_id)
