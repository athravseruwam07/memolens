import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, Date,
    ForeignKey, UniqueConstraint, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    hashed_password = Column(Text, nullable=False)
    role = Column(Text, nullable=False)  # 'caregiver' | 'patient'
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    age = Column(Integer, nullable=True)
    primary_caregiver = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    emergency_contact = Column(JSONB, nullable=True)  # { name, phone }
    tracked_items = Column(ARRAY(Text), nullable=True)  # ['keys','phone','wallet']
    common_issues = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    caregivers = relationship("PatientCaregiver", back_populates="patient", cascade="all, delete-orphan")


class PatientCaregiver(Base):
    __tablename__ = "patient_caregivers"

    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), primary_key=True)
    caregiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(Text, nullable=False)  # 'PRIMARY' | 'SECONDARY'
    invited_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    patient = relationship("Patient", back_populates="caregivers")
    caregiver = relationship("User")


class CaregiverInvite(Base):
    __tablename__ = "caregiver_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    invited_email = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="SECONDARY")
    token_hash = Column(Text, nullable=False, unique=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)


class FamiliarPerson(Base):
    __tablename__ = "familiar_people"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    relationship = Column(Text, nullable=True)
    photos = Column(ARRAY(Text), nullable=True)  # storage URLs
    face_embeddings = Column(JSONB, nullable=True)  # list of 128-d vectors
    notes = Column(Text, nullable=True)
    conversation_prompt = Column(Text, nullable=True)
    importance_level = Column(Integer, default=3)  # 1 to 5
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class ItemState(Base):
    __tablename__ = "item_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(Text, nullable=False)
    last_seen_room = Column(Text, nullable=True)
    last_seen_at = Column(TIMESTAMP(timezone=True), nullable=True)
    snapshot_url = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("patient_id", "item_name", name="uq_patient_item"),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=True)  # 'time' | 'person' | 'location' | 'object' | 'note'
    trigger_meta = Column(JSONB, nullable=True)
    message = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=True)  # 'face_recognized' | 'item_seen' | 'reminder_triggered' | 'query'
    payload = Column(JSONB, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class DailyNote(Base):
    __tablename__ = "daily_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    note_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
