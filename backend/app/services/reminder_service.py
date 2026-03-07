"""
Reminder trigger logic.
Checks active reminders against current context and returns triggered ones.
"""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.db import Reminder


async def get_triggered_time_reminders(db: AsyncSession, patient_id: UUID) -> list[Reminder]:
    """Get time-based reminders that should fire now (matching current HH:MM)."""
    now_time = datetime.utcnow().strftime("%H:%M")
    result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active == True,
            Reminder.type == "time",
        )
    )
    reminders = result.scalars().all()
    triggered = []
    for r in reminders:
        meta = r.trigger_meta or {}
        if meta.get("time") == now_time:
            triggered.append(r)
    return triggered


async def get_person_reminders(db: AsyncSession, patient_id: UUID, person_id: str) -> list[Reminder]:
    """Get reminders triggered by recognizing a specific person."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active == True,
            Reminder.type == "person",
        )
    )
    reminders = result.scalars().all()
    triggered = []
    for r in reminders:
        meta = r.trigger_meta or {}
        if meta.get("person_id") == person_id:
            triggered.append(r)
    return triggered
