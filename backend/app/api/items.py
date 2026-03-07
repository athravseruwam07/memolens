from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import User, ItemState
from app.models.schemas import ItemStateOut, APIResponse

router = APIRouter(prefix="/patients/{patient_id}/item-states", tags=["items"])


@router.get("/")
async def list_item_states(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ItemState).where(ItemState.patient_id == patient_id)
    )
    items = result.scalars().all()
    return APIResponse(data=[ItemStateOut.model_validate(i).model_dump() for i in items])
