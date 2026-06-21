from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import TenantOwnedMixin, TimestampMixin, new_uuid


class LabImagingResult(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "lab_imaging_result"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("encounter.id"), nullable=True)
    result_type: Mapped[str] = mapped_column(String(16), nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    code_display: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dicom_study_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="final", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClinicalReport(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "clinical_report"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=True
    )
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    format: Mapped[str] = mapped_column(String(16), default="html", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    report_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class ExportJob(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "export_job"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="patient", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    requested_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ErasureRequest(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "erasure_request"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    reviewed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "notification"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), default="in_app", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RetentionPolicy(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "retention_policy"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    erasure_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
