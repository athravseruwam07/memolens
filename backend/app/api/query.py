from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import ensure_patient_access, get_current_user
from app.models.db import Event, User
from app.models.schemas import QueryRequest, QueryResponse, APIResponse
from app.services.query_service import process_query
from app.services.voice_query import process_voice_query

router = APIRouter(tags=["query"])


class VoiceQueryRequest(BaseModel):
    """Request body for voice queries."""
    patient_id: UUID
    query: str


class VoiceQueryResponse(BaseModel):
    """Response body for voice queries - optimized for TTS."""
    type: str
    message: str
    results: Optional[Any] = None


@router.post("/query")
async def memory_query(
    body: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a memory query and return structured results.
    Used for text-based queries in the patient app.
    """
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


@router.post("/voice/query")
async def voice_query(
    body: VoiceQueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a voice query and return a speakable response (authenticated).
    
    This endpoint is optimized for voice interfaces:
    - Returns a natural language 'message' field ready for TTS
    - Detects intent from natural speech
    - Provides concise, spoken-friendly responses
    
    Request body:
        patient_id: UUID of the patient
        query: The transcribed voice query (e.g., "Where are my keys?")
    
    Response:
        type: Query result type (item_location, person_recognized, reminders, etc.)
        message: Natural language response ready for text-to-speech
        results: Structured data for display (optional)
    """
    await ensure_patient_access(db=db, user=user, patient_id=body.patient_id)
    result = await process_voice_query(db, body.patient_id, body.query)

    response = VoiceQueryResponse(
        type=result.get("type", "unknown"),
        message=result.get("message", "I couldn't process that request."),
        results=result.get("results")
    )
    return APIResponse(data=response.model_dump())


@router.post("/voice/query/device")
async def voice_query_device(
    body: VoiceQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a voice query from a trusted device (no auth required).
    
    This endpoint is for the Pi wearable device which doesn't have user credentials.
    It trusts that the device has the correct patient_id.
    
    Request body:
        patient_id: UUID of the patient
        query: The transcribed voice query
    
    Response:
        type: Query result type
        message: Natural language response ready for text-to-speech
        results: Structured data (optional)
    """
    result = await process_voice_query(db, body.patient_id, body.query)

    response = VoiceQueryResponse(
        type=result.get("type", "unknown"),
        message=result.get("message", "I couldn't process that request."),
        results=result.get("results")
    )
    return APIResponse(data=response.model_dump())
