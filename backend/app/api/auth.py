from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import User, PatientCaregiver
from app.models.schemas import (
    RegisterRequest, LoginRequest, InviteCaregiverRequest,
    UserOut, AuthResponse, APIResponse,
)
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        return APIResponse(error="Email already registered")

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return APIResponse(data=AuthResponse(user=UserOut.model_validate(user), token=token).model_dump())


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        return APIResponse(error="Invalid email or password")

    token = create_access_token(str(user.id))
    return APIResponse(data=AuthResponse(user=UserOut.model_validate(user), token=token).model_dump())


@router.post("/invite-caregiver")
async def invite_caregiver(
    body: InviteCaregiverRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify the current user is PRIMARY caregiver for the specified patient
    link_check = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == body.patient_id,
            PatientCaregiver.caregiver_id == user.id,
            PatientCaregiver.role == "PRIMARY",
        )
    )
    if not link_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Primary caregiver access required")
    # Check if invited user exists; if not, create a placeholder account
    result = await db.execute(select(User).where(User.email == body.email))
    invited_user = result.scalar_one_or_none()

    if not invited_user:
        invited_user = User(
            email=body.email,
            name=body.email.split("@")[0],
            hashed_password=hash_password("changeme"),  # placeholder
            role="caregiver",
        )
        db.add(invited_user)
        await db.commit()
        await db.refresh(invited_user)

    # Check if already linked
    existing_link = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == body.patient_id,
            PatientCaregiver.caregiver_id == invited_user.id,
        )
    )
    if existing_link.scalar_one_or_none():
        return APIResponse(error="Caregiver already linked to this patient")

    link = PatientCaregiver(
        patient_id=body.patient_id,
        caregiver_id=invited_user.id,
        role="SECONDARY",
    )
    db.add(link)
    await db.commit()

    return APIResponse(data={"message": "Caregiver invited", "caregiver_id": str(invited_user.id)})
