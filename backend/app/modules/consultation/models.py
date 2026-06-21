from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import TenantOwnedMixin, TimestampMixin, new_uuid


class ConsentRecord(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "consent_record"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("encounter.id"), nullable=True)
    scopes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class ConsultationSession(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "consultation_session"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    encounter_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("encounter.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    clinic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinic.id"), nullable=False)
    clinician_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    recovery_checkpoint: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionRecording(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "session_recording"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TranscriptSegment(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "transcript_segment"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ClinicalNote(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "clinical_note"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    encounter_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("encounter.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    addendum_of_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinical_note.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
