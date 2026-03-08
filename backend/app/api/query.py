from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import ensure_patient_access, get_current_user
from app.models.db import Event, User
from app.models.schemas import QueryRequest, QueryResponse, APIResponse
from app.services.query_service import process_query

router = APIRouter(tags=["query"])


@router.post("/query")
async def memory_query(
    body: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_patient_access(db=db, user=user, patient_id=body.patient_id)
    result = await process_query(db, body.patient_id, body.question)
    db.add(
        Event(
            patient_id=body.patient_id,
            type="query",
            payload={
                "question": body.question,
                "answer_type": result.get("answer_type"),
            },
        )
    )
    await db.commit()

    response = QueryResponse(
        question=body.question,
        answer_type=result["answer_type"],
        results=result["results"],
    )
    return APIResponse(data=response.model_dump())
