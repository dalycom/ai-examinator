from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import TenantOwnedMixin, TimestampMixin, new_uuid


class AIProvenance(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "ai_provenance"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AIExtractionRun(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "ai_extraction_run"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_note: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    provenance_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_provenance.id"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExtractedFact(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "extracted_fact"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    extraction_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_extraction_run.id"), nullable=False
    )
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_segment_ref: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("transcript_segment.id"), nullable=False
    )
    confidence_level: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    provenance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_provenance.id"), nullable=False
    )


class AISuggestion(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "ai_suggestion"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("consultation_session.id"), nullable=False
    )
    extraction_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_extraction_run.id"), nullable=False
    )
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    concept: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    supporting_facts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    missing_information: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    conflicting_information: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence_level: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    red_flag_warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_references: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    uncertainty_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    decided_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    provenance_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_provenance.id"), nullable=False
    )


class FeatureFlag(Base, TimestampMixin, TenantOwnedMixin):
    __tablename__ = "feature_flag"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_version"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class EvalDataset(Base, TimestampMixin):
    __tablename__ = "eval_dataset"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    is_synthetic: Mapped[bool] = mapped_column(default=True, nullable=False)


class EvalRun(Base, TimestampMixin):
    __tablename__ = "eval_run"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    dataset_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("eval_dataset.id"), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    passed_gates: Mapped[bool] = mapped_column(default=False, nullable=False)
