from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import JWT_SECRET, JWT_ALGORITHM
from app.database import get_db
from app.models.db import User, PatientCaregiver

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_caregiver(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "caregiver":
        raise HTTPException(status_code=403, detail="Caregiver role required")
    return user


async def ensure_patient_access(
    db: AsyncSession,
    user: User,
    patient_id: UUID,
) -> None:
    # Allow access only if the user is linked to the patient as primary/secondary caregiver.
    result = await db.execute(
        select(PatientCaregiver).where(
            PatientCaregiver.patient_id == patient_id,
            PatientCaregiver.caregiver_id == user.id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=403, detail="Patient access denied")


class RequirePatientAccess:
    """Dependency that checks the user has access to the given patient."""

    async def __call__(
        self,
        patient_id: UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        await ensure_patient_access(db=db, user=user, patient_id=patient_id)
        return user


class RequirePrimaryCaregiver:
    """Dependency that checks the user is the PRIMARY caregiver of a given patient."""

    async def __call__(
        self,
        patient_id: UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(
            select(PatientCaregiver).where(
                PatientCaregiver.patient_id == patient_id,
                PatientCaregiver.caregiver_id == user.id,
                PatientCaregiver.role == "PRIMARY",
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise HTTPException(status_code=403, detail="Primary caregiver access required")
        return user


require_primary_caregiver = RequirePrimaryCaregiver()
require_patient_access = RequirePatientAccess()
