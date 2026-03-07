from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import User
from app.models.schemas import QueryRequest, QueryResponse, APIResponse
from app.services.query_service import process_query

router = APIRouter(tags=["query"])


@router.post("/query")
async def memory_query(
    body: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await process_query(db, body.patient_id, body.question)
    response = QueryResponse(
        question=body.question,
        answer_type=result["answer_type"],
        results=result["results"],
    )
    return APIResponse(data=response.model_dump())
