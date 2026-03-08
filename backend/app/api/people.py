import asyncio
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.dependencies import require_patient_access
from app.models.db import User, FamiliarPerson
from app.models.schemas import (
    FamiliarPersonCreate, FamiliarPersonUpdate, FamiliarPersonOut, APIResponse,
)
from app.services.face_service import generate_face_embedding
from app.services.storage_service import upload_person_photo

router = APIRouter(prefix="/patients/{patient_id}/people", tags=["people"])


def _is_zero_embedding(embedding: list[float]) -> bool:
    return not embedding or all(abs(v) < 1e-12 for v in embedding)


@router.get("/")
async def list_people(
    patient_id: UUID,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamiliarPerson).where(FamiliarPerson.patient_id == patient_id)
    )
    people = result.scalars().all()
    return APIResponse(data=[FamiliarPersonOut.model_validate(p).model_dump() for p in people])


@router.post("/")
async def create_person(
    patient_id: UUID,
    name: str = Form(...),
    relationship: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    conversation_prompt: Optional[str] = Form(None),
    importance_level: int = Form(3),
    photos: list[UploadFile] = File(default=[]),
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    if not photos:
        raise HTTPException(status_code=400, detail="At least one face photo is required")

    person_id = uuid4()
    photo_urls = []
    embeddings = []

    encoded_photos: list[tuple[str, bytes, list[float]]] = []
    for photo in photos:
        content = await photo.read()
        embedding = await asyncio.to_thread(generate_face_embedding, content)
        if _is_zero_embedding(embedding):
            raise HTTPException(
                status_code=400,
                detail=f"No face detected in photo: {photo.filename or 'unnamed-file'}",
            )
        encoded_photos.append((photo.filename or "photo.jpg", content, embedding))

    for filename, content, embedding in encoded_photos:
        photo_url = await upload_person_photo(
            patient_id=str(patient_id),
            person_id=str(person_id),
            filename=filename,
            content=content,
        )
        photo_urls.append(photo_url)
        embeddings.append(embedding)

    person = FamiliarPerson(
        id=person_id,
        patient_id=patient_id,
        name=name,
        relationship=relationship,
        photos=photo_urls if photo_urls else None,
        face_embeddings=embeddings if embeddings else None,
        notes=notes,
        conversation_prompt=conversation_prompt,
        importance_level=importance_level,
        created_by=user.id,
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)

    return APIResponse(data=FamiliarPersonOut.model_validate(person).model_dump())


@router.patch("/{pid}")
async def update_person(
    patient_id: UUID,
    pid: UUID,
    body: FamiliarPersonUpdate,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamiliarPerson).where(
            FamiliarPerson.id == pid,
            FamiliarPerson.patient_id == patient_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(person, key, value)

    await db.commit()
    await db.refresh(person)
    return APIResponse(data=FamiliarPersonOut.model_validate(person).model_dump())


@router.delete("/{pid}")
async def delete_person(
    patient_id: UUID,
    pid: UUID,
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamiliarPerson).where(
            FamiliarPerson.id == pid,
            FamiliarPerson.patient_id == patient_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    await db.delete(person)
    await db.commit()
    return APIResponse(data={"message": "Person deleted"})


@router.post("/{pid}/photos")
async def upload_photos(
    patient_id: UUID,
    pid: UUID,
    photos: list[UploadFile] = File(...),
    user: User = Depends(require_patient_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamiliarPerson).where(
            FamiliarPerson.id == pid,
            FamiliarPerson.patient_id == patient_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    existing_photos = list(person.photos or [])
    existing_embeddings = list(person.face_embeddings or [])

    encoded_photos: list[tuple[str, bytes, list[float]]] = []
    for photo in photos:
        content = await photo.read()
        embedding = await asyncio.to_thread(generate_face_embedding, content)
        if _is_zero_embedding(embedding):
            raise HTTPException(
                status_code=400,
                detail=f"No face detected in photo: {photo.filename or 'unnamed-file'}",
            )
        encoded_photos.append((photo.filename or "photo.jpg", content, embedding))

    for filename, content, embedding in encoded_photos:
        photo_url = await upload_person_photo(
            patient_id=str(patient_id),
            person_id=str(pid),
            filename=filename,
            content=content,
        )
        existing_photos.append(photo_url)
        existing_embeddings.append(embedding)

    person.photos = existing_photos
    person.face_embeddings = existing_embeddings

    await db.commit()
    await db.refresh(person)
    return APIResponse(data=FamiliarPersonOut.model_validate(person).model_dump())
