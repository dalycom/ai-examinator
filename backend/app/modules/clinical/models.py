from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import DataClassification
from app.core.models import TenantOwnedMixin, TimestampMixin, new_uuid


class Patient(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "patient"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    clinic_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinic.id"), nullable=True)
    mrn: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    given_name: Mapped[str] = mapped_column(String(128), nullable=False)
    family_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contact: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preferred_locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class MedicalHistoryEntry(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "medical_history_entry"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Allergy(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "allergy"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    substance_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    substance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Medication(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "medication"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    drug_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Problem(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "problem"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    icd10_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class VitalSign(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "vital_sign"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    loinc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vital_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Appointment(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "appointment"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    clinic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinic.id"), nullable=False)
    clinician_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Encounter(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "encounter"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    clinic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinic.id"), nullable=False)
    clinician_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("appointment.id"), nullable=True
    )
    encounter_type: Mapped[str] = mapped_column(String(32), default="outpatient", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "document"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("encounter.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_classification: Mapped[str] = mapped_column(
        String(32), default=DataClassification.PHI.value, nullable=False
    )
