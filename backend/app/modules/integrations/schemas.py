from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LabImagingCreateRequest(BaseModel):
    result_type: Literal["lab", "imaging"]
    loinc_code: str | None = None
    code_display: str = Field(min_length=1, max_length=255)
    value: str | None = None
    unit: str | None = None
    dicom_study_uid: str | None = None
    encounter_id: UUID | None = None
    status: str = "final"
    observed_at: datetime | None = None


class LabImagingResponse(BaseModel):
    id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    result_type: str
    loinc_code: str | None
    code_display: str
    value: str | None
    unit: str | None
    dicom_study_uid: str | None
    status: str
    observed_at: datetime


class DashboardSummaryResponse(BaseModel):
    patients_total: int
    encounters_total: int
    consultations_completed: int
    pending_ai_reviews: int
    appointments_upcoming: int
    export_jobs_pending: int
    erasure_requests_pending: int
    unread_notifications: int


class DashboardPatientSnippet(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    status: str
    preferred_locale: str
    updated_at: datetime


class DashboardActivityItem(BaseModel):
    id: str
    kind: str
    title: str
    subtitle: str
    occurred_at: datetime
    patient_id: UUID | None = None


class DashboardAiStatus(BaseModel):
    extraction_enabled: bool
    suggestions_enabled: bool
    red_flags_enabled: bool
    pending_reviews: int
    eval_passed: bool
    provider: str


class DashboardOverviewResponse(BaseModel):
    summary: DashboardSummaryResponse
    recent_patients: list[DashboardPatientSnippet]
    activity: list[DashboardActivityItem]
    ai_status: DashboardAiStatus
    consultations_in_progress: int
    signed_notes_total: int


class ReportGenerateRequest(BaseModel):
    patient_id: UUID
    session_id: UUID | None = None
    locale: str = "en"
    format: Literal["html", "pdf"] = "html"


class ReportResponse(BaseModel):
    id: UUID
    patient_id: UUID
    session_id: UUID | None
    locale: str
    format: str
    title: str
    body_html: str
    report_metadata: dict[str, Any]


class ExportJobCreateRequest(BaseModel):
    patient_id: UUID | None = None
    scope: Literal["patient", "organization"] = "patient"


class ExportJobResponse(BaseModel):
    id: UUID
    patient_id: UUID | None
    scope: str
    status: str
    requested_by: UUID
    result_summary: dict[str, Any] | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime


class ErasureRequestCreate(BaseModel):
    patient_id: UUID
    reason: str = Field(min_length=3)


class ErasureReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = None


class ErasureRequestResponse(BaseModel):
    id: UUID
    patient_id: UUID
    status: str
    reason: str
    requested_by: UUID
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    link_path: str | None
    is_read: bool
    channel: str
    created_at: datetime


class RetentionPolicyResponse(BaseModel):
    id: UUID
    resource_type: str
    retention_days: int
    erasure_enabled: bool


class RetentionPolicyUpdateRequest(BaseModel):
    retention_days: int = Field(ge=1, le=36500)
    erasure_enabled: bool = True


class GovernanceDashboardResponse(BaseModel):
    feature_flags: list[dict[str, Any]]
    pending_ai_suggestions: int
    recent_eval_runs: list[dict[str, Any]]
    retention_policies: list[RetentionPolicyResponse]
