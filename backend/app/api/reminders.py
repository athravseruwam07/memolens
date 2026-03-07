from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_patient_access
from app.models.db import User, Reminder
from app.models.schemas import ReminderCreate, ReminderUpdate, ReminderOut, APIResponse

router = APIRouter(prefix="/patients/{patient_id}/reminders", tags=["reminders"])


@router.get("/")
async def list_reminders(
    patient_id: UUID,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.patient_id == patient_id)
    )
    reminders = result.scalars().all()
    return APIResponse(data=[ReminderOut.model_validate(r).model_dump() for r in reminders])


@router.post("/")
async def create_reminder(
    patient_id: UUID,
    body: ReminderCreate,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        patient_id=patient_id,
        type=body.type,
        trigger_meta=body.trigger_meta,
        message=body.message,
        active=body.active,
        created_by=user.id,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return APIResponse(data=ReminderOut.model_validate(reminder).model_dump())


@router.patch("/{rid}")
async def update_reminder(
    patient_id: UUID,
    rid: UUID,
    body: ReminderUpdate,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.id == rid, Reminder.patient_id == patient_id)
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reminder, key, value)

    await db.commit()
    await db.refresh(reminder)
    return APIResponse(data=ReminderOut.model_validate(reminder).model_dump())


@router.delete("/{rid}")
async def delete_reminder(
    patient_id: UUID,
    rid: UUID,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.id == rid, Reminder.patient_id == patient_id)
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    await db.delete(reminder)
    await db.commit()
    return APIResponse(data={"message": "Reminder deleted"})
