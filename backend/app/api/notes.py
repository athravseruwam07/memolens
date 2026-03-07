from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.dependencies import require_patient_access
from app.models.db import User, DailyNote
from app.models.schemas import DailyNoteCreate, DailyNoteOut, APIResponse

router = APIRouter(prefix="/patients/{patient_id}/daily-notes", tags=["notes"])


@router.get("/")
async def list_notes(
    patient_id: UUID,
    date_filter: Optional[date] = Query(None, alias="date"),
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    query = select(DailyNote).where(DailyNote.patient_id == patient_id)
    if date_filter:
        query = query.where(DailyNote.note_date == date_filter)

    result = await db.execute(query)
    notes = result.scalars().all()
    return APIResponse(data=[DailyNoteOut.model_validate(n).model_dump() for n in notes])


@router.post("/")
async def create_note(
    patient_id: UUID,
    body: DailyNoteCreate,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    note = DailyNote(
        patient_id=patient_id,
        note_date=date.today(),
        content=body.content,
        created_by=user.id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return APIResponse(data=DailyNoteOut.model_validate(note).model_dump())
