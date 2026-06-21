from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.integrations.schemas import (
    DashboardOverviewResponse,
    DashboardSummaryResponse,
    ErasureRequestCreate,
    ErasureRequestResponse,
    ErasureReviewRequest,
    ExportJobCreateRequest,
    ExportJobResponse,
    GovernanceDashboardResponse,
    LabImagingCreateRequest,
    LabImagingResponse,
    NotificationResponse,
    ReportGenerateRequest,
    ReportResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
)
from app.modules.integrations.service import IntegrationsService

router = APIRouter(tags=["integrations"])


@router.get("/patients/{patient_id}/lab-imaging-results", response_model=list[LabImagingResponse])
def list_lab_imaging(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[LabImagingResponse]:
    return IntegrationsService(db).list_lab_imaging(principal, patient_id)


@router.post(
    "/patients/{patient_id}/lab-imaging-results",
    response_model=LabImagingResponse,
    status_code=201,
)
def create_lab_imaging(
    patient_id: UUID,
    payload: LabImagingCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> LabImagingResponse:
    service = IntegrationsService(db)
    result = service.create_lab_imaging(principal, patient_id, payload)
    db.commit()
    return result


@router.get("/fhir/Patient/{patient_id}")
def fhir_patient(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return IntegrationsService(db).fhir_patient(principal, patient_id)


@router.get("/fhir/Encounter/{encounter_id}")
def fhir_encounter(
    encounter_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return IntegrationsService(db).fhir_encounter(principal, encounter_id)


@router.get("/fhir/Observation")
def fhir_observations(
    patient: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return IntegrationsService(db).fhir_patient_observations(principal, patient)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return IntegrationsService(db).dashboard_summary(principal)


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def dashboard_overview(
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    service = IntegrationsService(db)
    overview = service.dashboard_overview(principal)
    db.commit()
    return overview


@router.post("/reports", response_model=ReportResponse, status_code=201)
def generate_report(
    payload: ReportGenerateRequest,
    principal: Principal = Depends(require_permission("note:read")),
    db: Session = Depends(get_db),
) -> ReportResponse:
    service = IntegrationsService(db)
    report = service.generate_report(principal, payload)
    db.commit()
    return report


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    principal: Principal = Depends(require_permission("note:read")),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return IntegrationsService(db).get_report(principal, report_id)


@router.post("/export-jobs", response_model=ExportJobResponse, status_code=201)
def create_export_job(
    payload: ExportJobCreateRequest,
    principal: Principal = Depends(require_permission("export:run")),
    db: Session = Depends(get_db),
) -> ExportJobResponse:
    service = IntegrationsService(db)
    job = service.create_export_job(principal, payload)
    db.commit()
    return job


@router.get("/export-jobs/{job_id}", response_model=ExportJobResponse)
def get_export_job(
    job_id: UUID,
    principal: Principal = Depends(require_permission("export:run")),
    db: Session = Depends(get_db),
) -> ExportJobResponse:
    return IntegrationsService(db).get_export_job(principal, job_id)


@router.get("/export-jobs/{job_id}/download")
def download_export_job(
    job_id: UUID,
    principal: Principal = Depends(require_permission("export:run")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return IntegrationsService(db).get_export_download(principal, job_id)


@router.get("/erasure-requests", response_model=list[ErasureRequestResponse])
def list_erasure_requests(
    principal: Principal = Depends(require_permission("erasure:run")),
    db: Session = Depends(get_db),
) -> list[ErasureRequestResponse]:
    return IntegrationsService(db).list_erasure_requests(principal)


@router.post("/erasure-requests", response_model=ErasureRequestResponse, status_code=201)
def create_erasure_request(
    payload: ErasureRequestCreate,
    principal: Principal = Depends(require_permission("erasure:run")),
    db: Session = Depends(get_db),
) -> ErasureRequestResponse:
    service = IntegrationsService(db)
    row = service.create_erasure_request(principal, payload)
    db.commit()
    return row


@router.post("/erasure-requests/{request_id}/review", response_model=ErasureRequestResponse)
def review_erasure_request(
    request_id: UUID,
    payload: ErasureReviewRequest,
    principal: Principal = Depends(require_permission("erasure:run")),
    db: Session = Depends(get_db),
) -> ErasureRequestResponse:
    service = IntegrationsService(db)
    row = service.review_erasure_request(principal, request_id, payload)
    db.commit()
    return row


@router.post("/erasure-requests/{request_id}/complete", response_model=ErasureRequestResponse)
def complete_erasure_request(
    request_id: UUID,
    principal: Principal = Depends(require_permission("erasure:run")),
    db: Session = Depends(get_db),
) -> ErasureRequestResponse:
    service = IntegrationsService(db)
    row = service.complete_erasure_request(principal, request_id)
    db.commit()
    return row


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    return IntegrationsService(db).list_notifications(principal)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    service = IntegrationsService(db)
    row = service.mark_notification_read(principal, notification_id)
    db.commit()
    return row


@router.get("/retention-policies", response_model=list[RetentionPolicyResponse])
def list_retention_policies(
    principal: Principal = Depends(require_permission("governance:manage")),
    db: Session = Depends(get_db),
) -> list[RetentionPolicyResponse]:
    service = IntegrationsService(db)
    policies = service.ensure_retention_policies(principal)
    db.commit()
    return policies


@router.put("/retention-policies/{resource_type}", response_model=RetentionPolicyResponse)
def update_retention_policy(
    resource_type: str,
    payload: RetentionPolicyUpdateRequest,
    principal: Principal = Depends(require_permission("governance:manage")),
    db: Session = Depends(get_db),
) -> RetentionPolicyResponse:
    service = IntegrationsService(db)
    row = service.update_retention_policy(principal, resource_type, payload)
    db.commit()
    return row


@router.get("/governance/dashboard", response_model=GovernanceDashboardResponse)
def governance_dashboard(
    principal: Principal = Depends(require_permission("governance:manage")),
    db: Session = Depends(get_db),
) -> GovernanceDashboardResponse:
    service = IntegrationsService(db)
    dashboard = service.governance_dashboard(principal)
    db.commit()
    return dashboard
