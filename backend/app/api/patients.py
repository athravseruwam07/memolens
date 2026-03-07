from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_caregiver, require_primary_caregiver
from app.models.db import User, Patient, PatientCaregiver
from app.models.schemas import (
    PatientCreate, PatientUpdate, PatientOut, CaregiverLink, APIResponse,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/")
async def create_patient(
    body: PatientCreate,
    user: User = Depends(require_caregiver),
    db: AsyncSession = Depends(get_db),
):
    patient = Patient(
        name=body.name,
        age=body.age,
        primary_caregiver=user.id,
        emergency_contact=body.emergency_contact,
        tracked_items=body.tracked_items,
        common_issues=body.common_issues,
    )
    db.add(patient)
    await db.flush()

    link = PatientCaregiver(
        patient_id=patient.id,
        caregiver_id=user.id,
        role="PRIMARY",
    )
    db.add(link)
    await db.commit()
    await db.refresh(patient)

    return APIResponse(data=PatientOut.model_validate(patient).model_dump())


@router.get("/{patient_id}")
async def get_patient(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return APIResponse(data=PatientOut.model_validate(patient).model_dump())


@router.patch("/{patient_id}")
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    user: User = Depends(require_primary_caregiver),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    await db.commit()
    await db.refresh(patient)
    return APIResponse(data=PatientOut.model_validate(patient).model_dump())


@router.get("/{patient_id}/caregivers")
async def list_caregivers(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatientCaregiver, User)
        .join(User, PatientCaregiver.caregiver_id == User.id)
        .where(PatientCaregiver.patient_id == patient_id)
    )
    rows = result.all()
    caregivers = [
        CaregiverLink(
            caregiver_id=link.caregiver_id,
            role=link.role,
            invited_at=link.invited_at,
            caregiver_name=u.name,
            caregiver_email=u.email,
        ).model_dump()
        for link, u in rows
    ]
    return APIResponse(data=caregivers)


@router.delete("/{patient_id}/caregivers/{uid}")
async def remove_caregiver(
    patient_id: UUID,
    uid: UUID,
    user: User = Depends(require_primary_caregiver),
    db: AsyncSession = Depends(get_db),
):
    # Cannot remove self (primary)
    if uid == user.id:
        return APIResponse(error="Cannot remove the primary caregiver")

    result = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == uid,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Caregiver link not found")

    await db.delete(link)
    await db.commit()
    return APIResponse(data={"message": "Caregiver removed"})
