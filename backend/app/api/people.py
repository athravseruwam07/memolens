from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import User, FamiliarPerson
from app.models.schemas import (
    FamiliarPersonCreate, FamiliarPersonUpdate, FamiliarPersonOut, APIResponse,
)
from app.services.face_service import generate_face_embedding

router = APIRouter(prefix="/patients/{patient_id}/people", tags=["people"])


@router.get("/")
async def list_people(
    patient_id: UUID,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    photo_urls = []
    embeddings = []
    for photo in photos:
        content = await photo.read()
        # In production: upload to Supabase Storage, get URL
        photo_urls.append(f"/uploads/{photo.filename}")
        embeddings.append(generate_face_embedding(content))

    person = FamiliarPerson(
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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

    for photo in photos:
        content = await photo.read()
        existing_photos.append(f"/uploads/{photo.filename}")
        existing_embeddings.append(generate_face_embedding(content))

    person.photos = existing_photos
    person.face_embeddings = existing_embeddings

    await db.commit()
    await db.refresh(person)
    return APIResponse(data=FamiliarPersonOut.model_validate(person).model_dump())
