from __future__ import annotations
from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


# --- Generic response wrapper ---

class APIResponse(BaseModel):
    data: Any = None
    error: Optional[str] = None


# --- Auth ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str  # 'caregiver' | 'patient'

class LoginRequest(BaseModel):
    email: str
    password: str

class InviteCaregiverRequest(BaseModel):
    patient_id: UUID
    email: str

class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}

class AuthResponse(BaseModel):
    user: UserOut
    token: str


# --- Patient ---

class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    emergency_contact: Optional[dict] = None
    tracked_items: Optional[list[str]] = None
    common_issues: Optional[str] = None

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    emergency_contact: Optional[dict] = None
    tracked_items: Optional[list[str]] = None
    common_issues: Optional[str] = None

class PatientOut(BaseModel):
    id: UUID
    name: str
    age: Optional[int]
    primary_caregiver: Optional[UUID]
    emergency_contact: Optional[dict]
    tracked_items: Optional[list[str]]
    common_issues: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class CaregiverLink(BaseModel):
    caregiver_id: UUID
    role: str
    invited_at: datetime
    caregiver_name: Optional[str] = None
    caregiver_email: Optional[str] = None


# --- Familiar People ---

class FamiliarPersonCreate(BaseModel):
    name: str
    relationship: Optional[str] = None
    notes: Optional[str] = None
    conversation_prompt: Optional[str] = None
    importance_level: Optional[int] = 3

class FamiliarPersonUpdate(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    notes: Optional[str] = None
    conversation_prompt: Optional[str] = None
    importance_level: Optional[int] = None

class FamiliarPersonOut(BaseModel):
    id: UUID
    patient_id: UUID
    name: str
    relationship: Optional[str]
    photos: Optional[list[str]]
    notes: Optional[str]
    conversation_prompt: Optional[str]
    importance_level: int
    created_by: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Item States ---

class ItemStateOut(BaseModel):
    id: UUID
    patient_id: UUID
    item_name: str
    last_seen_room: Optional[str]
    last_seen_at: Optional[datetime]
    snapshot_url: Optional[str]
    confidence: Optional[float]

    model_config = {"from_attributes": True}


# --- Reminders ---

class ReminderCreate(BaseModel):
    type: Optional[str] = None
    trigger_meta: Optional[dict] = None
    message: str
    active: Optional[bool] = True

class ReminderUpdate(BaseModel):
    type: Optional[str] = None
    trigger_meta: Optional[dict] = None
    message: Optional[str] = None
    active: Optional[bool] = None

class ReminderOut(BaseModel):
    id: UUID
    patient_id: UUID
    type: Optional[str]
    trigger_meta: Optional[dict]
    message: str
    active: bool
    created_by: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Events ---

class EventCreate(BaseModel):
    patient_id: UUID
    type: str
    payload: Optional[dict] = None

class EventOut(BaseModel):
    id: UUID
    patient_id: UUID
    type: Optional[str]
    payload: Optional[dict]
    occurred_at: datetime

    model_config = {"from_attributes": True}


# --- Daily Notes ---

class DailyNoteCreate(BaseModel):
    content: str

class DailyNoteOut(BaseModel):
    id: UUID
    patient_id: UUID
    note_date: date
    content: str
    created_by: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Query ---

class QueryRequest(BaseModel):
    patient_id: UUID
    question: str

class QueryResponse(BaseModel):
    question: str
    answer_type: str
    results: Any
