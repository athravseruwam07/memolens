from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import User, Event
from app.models.schemas import EventCreate, EventOut, APIResponse

router = APIRouter(tags=["events"])


@router.post("/events")
async def create_event(
    body: EventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = Event(
        patient_id=body.patient_id,
        type=body.type,
        payload=body.payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return APIResponse(data=EventOut.model_validate(event).model_dump())


@router.get("/patients/{patient_id}/events")
async def list_events(
    patient_id: UUID,
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).where(Event.patient_id == patient_id)
    if type:
        query = query.where(Event.type == type)
    query = query.order_by(desc(Event.occurred_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    events = result.scalars().all()
    return APIResponse(data=[EventOut.model_validate(e).model_dump() for e in events])
