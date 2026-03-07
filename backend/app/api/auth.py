import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import INVITE_EXPIRE_HOURS
from app.database import get_db
from app.dependencies import get_current_user
from app.models.db import CaregiverInvite, User, PatientCaregiver
from app.models.schemas import (
    AcceptInviteRequest,
    AcceptInviteResponse,
    AuthResponse,
    APIResponse,
    InviteCaregiverRequest,
    InviteCaregiverResponse,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
    invited_email = body.email.lower().strip()

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

    if invited_email == user.email.lower().strip():
        return APIResponse(error="You are already a caregiver for this patient")

    existing_user_result = await db.execute(select(User).where(User.email == invited_email))
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        if existing_user.role == "patient":
            return APIResponse(error="Cannot invite a patient account as caregiver")
        existing_link = await db.execute(
            select(PatientCaregiver).where(
                PatientCaregiver.patient_id == body.patient_id,
                PatientCaregiver.caregiver_id == existing_user.id,
            )
        )
        if existing_link.scalar_one_or_none():
            return APIResponse(error="Caregiver already linked to this patient")

    now = datetime.now(timezone.utc)
    stale_invites = await db.execute(
        select(CaregiverInvite).where(
            CaregiverInvite.patient_id == body.patient_id,
            CaregiverInvite.invited_email == invited_email,
            CaregiverInvite.accepted_at.is_(None),
            CaregiverInvite.revoked_at.is_(None),
        )
    )
    for inv in stale_invites.scalars().all():
        inv.revoked_at = now

    invite_token = secrets.token_urlsafe(32)
    invite = CaregiverInvite(
        patient_id=body.patient_id,
        invited_email=invited_email,
        role="SECONDARY",
        token_hash=_hash_invite_token(invite_token),
        invited_by=user.id,
        expires_at=now + timedelta(hours=INVITE_EXPIRE_HOURS),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    response = InviteCaregiverResponse(
        message="Caregiver invite created",
        invite_token=invite_token,
        expires_at=invite.expires_at,
    )
    return APIResponse(data=response.model_dump())


@router.post("/accept-invite")
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = _hash_invite_token(body.token.strip())
    result = await db.execute(
        select(CaregiverInvite).where(
            CaregiverInvite.token_hash == token_hash,
            CaregiverInvite.revoked_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        return APIResponse(error="Invalid invite token")

    now = datetime.now(timezone.utc)
    if invite.accepted_at is not None:
        return APIResponse(error="Invite token already used")
    if invite.expires_at < now:
        return APIResponse(error="Invite token expired")

    existing_user_result = await db.execute(
        select(User).where(User.email == invite.invited_email)
    )
    user = existing_user_result.scalar_one_or_none()

    if user:
        if user.role == "patient":
            return APIResponse(error="Patient accounts cannot accept caregiver invites")
    else:
        if not body.name or not body.password:
            return APIResponse(error="Name and password are required for new invited users")
        user = User(
            email=invite.invited_email,
            name=body.name,
            hashed_password=hash_password(body.password),
            role="caregiver",
        )
        db.add(user)
        await db.flush()

    existing_link = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == invite.patient_id,
            PatientCaregiver.caregiver_id == user.id,
        )
    )
    if not existing_link.scalar_one_or_none():
        link = PatientCaregiver(
            patient_id=invite.patient_id,
            caregiver_id=user.id,
            role=invite.role,
        )
        db.add(link)

    invite.accepted_at = now
    invite.accepted_by = user.id
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    response = AcceptInviteResponse(
        message="Invite accepted",
        patient_id=invite.patient_id,
        user=UserOut.model_validate(user),
        token=token,
    )
    return APIResponse(data=response.model_dump())
