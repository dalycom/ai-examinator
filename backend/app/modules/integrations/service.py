import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func

from app.core.config import get_settings
from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.ai.governance import GovernanceService
from app.modules.ai.models import AISuggestion, EvalRun
from app.modules.audit.service import AuditService
from app.modules.clinical.models import (
    Allergy,
    Appointment,
    Encounter,
    MedicalHistoryEntry,
    Medication,
    Patient,
    Problem,
    VitalSign,
)
from app.modules.consultation.models import ClinicalNote, ConsultationSession
from app.modules.integrations import fhir_mapper
from app.modules.integrations.models import (
    ClinicalReport,
    ErasureRequest,
    ExportJob,
    LabImagingResult,
    Notification,
    RetentionPolicy,
)
from app.modules.integrations.schemas import (
    DashboardActivityItem,
    DashboardAiStatus,
    DashboardOverviewResponse,
    DashboardPatientSnippet,
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
from sqlalchemy.orm import Session

DEFAULT_RETENTION: dict[str, int] = {
    "patient": 3650,
    "consultation_session": 2555,
    "clinical_report": 2555,
    "export_job": 90,
    "audit_log": 2555,
}

REPORT_TITLES: dict[str, str] = {
    "en": "Clinical summary report",
    "ar": "تقرير ملخص سريري",
    "fr": "Rapport de synthèse clinique",
}


class IntegrationsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.settings = get_settings()

    def list_lab_imaging(self, principal: Principal, patient_id: UUID) -> list[LabImagingResponse]:
        with tenant_session(self.db, principal.organization_id):
            fhir_mapper.get_patient_or_404(self.db, principal.organization_id, patient_id)
            rows = (
                self.db.query(LabImagingResult)
                .filter(
                    LabImagingResult.patient_id == patient_id,
                    LabImagingResult.organization_id == principal.organization_id,
                    LabImagingResult.deleted_at.is_(None),
                )
                .order_by(LabImagingResult.observed_at.desc())
                .all()
            )
            return [self._lab_to_response(row) for row in rows]

    def create_lab_imaging(
        self, principal: Principal, patient_id: UUID, payload: LabImagingCreateRequest
    ) -> LabImagingResponse:
        with tenant_session(self.db, principal.organization_id):
            fhir_mapper.get_patient_or_404(self.db, principal.organization_id, patient_id)
            if payload.encounter_id is not None:
                fhir_mapper.get_encounter_or_404(self.db, principal.organization_id, payload.encounter_id)
            row = LabImagingResult(
                organization_id=principal.organization_id,
                patient_id=patient_id,
                encounter_id=payload.encounter_id,
                result_type=payload.result_type,
                loinc_code=payload.loinc_code,
                code_display=payload.code_display,
                value=payload.value,
                unit=payload.unit,
                dicom_study_uid=payload.dicom_study_uid,
                status=payload.status,
                observed_at=payload.observed_at or datetime.now(tz=UTC),
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(row)
            self.db.flush()
            self.audit.record(
                action="lab_imaging.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="lab_imaging_result",
                resource_id=row.id,
            )
            return self._lab_to_response(row)

    def fhir_patient(self, principal: Principal, patient_id: UUID) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = fhir_mapper.get_patient_or_404(self.db, principal.organization_id, patient_id)
            return fhir_mapper.patient_to_fhir(patient)

    def fhir_encounter(self, principal: Principal, encounter_id: UUID) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            encounter = fhir_mapper.get_encounter_or_404(self.db, principal.organization_id, encounter_id)
            return fhir_mapper.encounter_to_fhir(encounter)

    def fhir_patient_observations(self, principal: Principal, patient_id: UUID) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            fhir_mapper.get_patient_or_404(self.db, principal.organization_id, patient_id)
            vitals = (
                self.db.query(VitalSign)
                .filter(
                    VitalSign.patient_id == patient_id,
                    VitalSign.organization_id == principal.organization_id,
                    VitalSign.deleted_at.is_(None),
                )
                .all()
            )
            labs = (
                self.db.query(LabImagingResult)
                .filter(
                    LabImagingResult.patient_id == patient_id,
                    LabImagingResult.organization_id == principal.organization_id,
                    LabImagingResult.deleted_at.is_(None),
                )
                .all()
            )
            entries = [fhir_mapper.observation_from_vital(v) for v in vitals]
            entries.extend(fhir_mapper.observation_from_lab_result(r) for r in labs)
            return fhir_mapper.bundle_from_entries(entries)

    def dashboard_summary(self, principal: Principal) -> DashboardSummaryResponse:
        with tenant_session(self.db, principal.organization_id):
            org_id = principal.organization_id
            now = datetime.now(tz=UTC)
            patients_total = (
                self.db.query(func.count(Patient.id))
                .filter(Patient.organization_id == org_id, Patient.deleted_at.is_(None))
                .scalar()
                or 0
            )
            encounters_total = (
                self.db.query(func.count(Encounter.id))
                .filter(Encounter.organization_id == org_id, Encounter.deleted_at.is_(None))
                .scalar()
                or 0
            )
            consultations_completed = (
                self.db.query(func.count(ConsultationSession.id))
                .filter(
                    ConsultationSession.organization_id == org_id,
                    ConsultationSession.status == "signed",
                    ConsultationSession.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            pending_ai_reviews = (
                self.db.query(func.count(AISuggestion.id))
                .filter(
                    AISuggestion.organization_id == org_id,
                    AISuggestion.decision_status == "pending",
                    AISuggestion.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            appointments_upcoming = (
                self.db.query(func.count(Appointment.id))
                .filter(
                    Appointment.organization_id == org_id,
                    Appointment.starts_at >= now,
                    Appointment.status == "scheduled",
                    Appointment.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            export_jobs_pending = (
                self.db.query(func.count(ExportJob.id))
                .filter(
                    ExportJob.organization_id == org_id,
                    ExportJob.status.in_(("pending", "running")),
                    ExportJob.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            erasure_requests_pending = (
                self.db.query(func.count(ErasureRequest.id))
                .filter(
                    ErasureRequest.organization_id == org_id,
                    ErasureRequest.status == "pending",
                    ErasureRequest.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            unread_notifications = (
                self.db.query(func.count(Notification.id))
                .filter(
                    Notification.organization_id == org_id,
                    Notification.user_id == principal.user_id,
                    Notification.is_read.is_(False),
                    Notification.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            return DashboardSummaryResponse(
                patients_total=patients_total,
                encounters_total=encounters_total,
                consultations_completed=consultations_completed,
                pending_ai_reviews=pending_ai_reviews,
                appointments_upcoming=appointments_upcoming,
                export_jobs_pending=export_jobs_pending,
                erasure_requests_pending=erasure_requests_pending,
                unread_notifications=unread_notifications,
            )

    def dashboard_overview(self, principal: Principal) -> DashboardOverviewResponse:
        from app.modules.ai.eval import run_stub_eval

        summary = self.dashboard_summary(principal)
        governance = GovernanceService(self.db)
        governance.ensure_default_flags(principal)
        flags = {row.key: row.enabled for row in governance.list_flags(principal)}
        eval_passed = run_stub_eval().passed

        with tenant_session(self.db, principal.organization_id):
            org_id = principal.organization_id
            recent_rows = (
                self.db.query(Patient)
                .filter(Patient.organization_id == org_id, Patient.deleted_at.is_(None))
                .order_by(Patient.updated_at.desc())
                .limit(6)
                .all()
            )
            recent_patients = [
                DashboardPatientSnippet(
                    id=row.id,
                    mrn=row.mrn,
                    given_name=row.given_name,
                    family_name=row.family_name,
                    status=row.status,
                    preferred_locale=row.preferred_locale,
                    updated_at=row.updated_at,
                )
                for row in recent_rows
            ]

            consultations_in_progress = (
                self.db.query(func.count(ConsultationSession.id))
                .filter(
                    ConsultationSession.organization_id == org_id,
                    ConsultationSession.status != "signed",
                    ConsultationSession.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            signed_notes_total = (
                self.db.query(func.count(ClinicalNote.id))
                .filter(
                    ClinicalNote.organization_id == org_id,
                    ClinicalNote.status == "signed",
                    ClinicalNote.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )

            activity: list[DashboardActivityItem] = []
            encounters = (
                self.db.query(Encounter)
                .filter(Encounter.organization_id == org_id, Encounter.deleted_at.is_(None))
                .order_by(Encounter.started_at.desc())
                .limit(5)
                .all()
            )
            for row in encounters:
                patient = self.db.get(Patient, row.patient_id)
                name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"
                activity.append(
                    DashboardActivityItem(
                        id=str(row.id),
                        kind="encounter",
                        title=f"Encounter — {name}",
                        subtitle=row.status.replace("_", " ").title(),
                        occurred_at=row.started_at,
                        patient_id=row.patient_id,
                    )
                )

            appointments = (
                self.db.query(Appointment)
                .filter(
                    Appointment.organization_id == org_id,
                    Appointment.deleted_at.is_(None),
                )
                .order_by(Appointment.starts_at.desc())
                .limit(5)
                .all()
            )
            for row in appointments:
                patient = self.db.get(Patient, row.patient_id)
                name = f"{patient.given_name} {patient.family_name}" if patient else "Patient"
                activity.append(
                    DashboardActivityItem(
                        id=str(row.id),
                        kind="appointment",
                        title=f"Appointment — {name}",
                        subtitle=row.status.replace("_", " ").title(),
                        occurred_at=row.starts_at,
                        patient_id=row.patient_id,
                    )
                )

            activity.sort(key=lambda item: item.occurred_at, reverse=True)
            activity = activity[:8]

            ai_status = DashboardAiStatus(
                extraction_enabled=flags.get("ai_extraction", True),
                suggestions_enabled=flags.get("ai_suggestions", True),
                red_flags_enabled=flags.get("ai_red_flags", True),
                pending_reviews=summary.pending_ai_reviews,
                eval_passed=eval_passed,
                provider=self.settings.llm_provider,
            )

            return DashboardOverviewResponse(
                summary=summary,
                recent_patients=recent_patients,
                activity=activity,
                ai_status=ai_status,
                consultations_in_progress=consultations_in_progress,
                signed_notes_total=signed_notes_total,
            )

    def generate_report(self, principal: Principal, payload: ReportGenerateRequest) -> ReportResponse:
        with tenant_session(self.db, principal.organization_id):
            patient = fhir_mapper.get_patient_or_404(self.db, principal.organization_id, payload.patient_id)
            session: ConsultationSession | None = None
            note: ClinicalNote | None = None
            if payload.session_id is not None:
                session = fhir_mapper.get_session_or_404(self.db, principal.organization_id, payload.session_id)
                if session.patient_id != patient.id:
                    raise AppError(
                        code="SESSION_PATIENT_MISMATCH",
                        message_key="errors.validation_failed",
                        status_code=400,
                    )
                note = fhir_mapper.get_note_for_session(self.db, principal.organization_id, payload.session_id)

            locale = payload.locale if payload.locale in ("en", "ar", "fr") else "en"
            dir_attr = "rtl" if locale == "ar" else "ltr"
            title = REPORT_TITLES.get(locale, REPORT_TITLES["en"])
            problems = (
                self.db.query(Problem)
                .filter(
                    Problem.patient_id == patient.id,
                    Problem.organization_id == principal.organization_id,
                    Problem.deleted_at.is_(None),
                )
                .limit(10)
                .all()
            )
            allergies = (
                self.db.query(Allergy)
                .filter(
                    Allergy.patient_id == patient.id,
                    Allergy.organization_id == principal.organization_id,
                    Allergy.deleted_at.is_(None),
                )
                .limit(10)
                .all()
            )
            body_html = self._render_report_html(
                locale=locale,
                dir_attr=dir_attr,
                patient=patient,
                problems=problems,
                allergies=allergies,
                note=note,
            )
            report = ClinicalReport(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                session_id=payload.session_id,
                locale=locale,
                format=payload.format,
                title=title,
                body_html=body_html,
                report_metadata={"generated_by": str(principal.user_id), "ai_labeled": False},
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(report)
            self.db.flush()
            self.audit.record(
                action="report.generate",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinical_report",
                resource_id=report.id,
            )
            return self._report_to_response(report)

    def get_report(self, principal: Principal, report_id: UUID) -> ReportResponse:
        with tenant_session(self.db, principal.organization_id):
            report = self._get_report_or_404(principal, report_id)
            return self._report_to_response(report)

    def create_export_job(self, principal: Principal, payload: ExportJobCreateRequest) -> ExportJobResponse:
        with tenant_session(self.db, principal.organization_id):
            if payload.scope == "patient":
                if payload.patient_id is None:
                    raise AppError(
                        code="PATIENT_REQUIRED",
                        message_key="errors.validation_failed",
                        status_code=422,
                    )
                fhir_mapper.get_patient_or_404(self.db, principal.organization_id, payload.patient_id)

            job = ExportJob(
                organization_id=principal.organization_id,
                patient_id=payload.patient_id,
                scope=payload.scope,
                status="pending",
                requested_by=principal.user_id,
                data_classification=DataClassification.SENSITIVE_PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(job)
            self.db.flush()
            self.audit.record(
                action="export.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="export_job",
                resource_id=job.id,
            )
            if self.settings.export_use_celery:
                from app.workers.tasks.export_tasks import run_export_job

                run_export_job.delay(str(job.id), str(principal.organization_id), str(principal.user_id))
            else:
                self.execute_export_job(job.id, principal)
            return self._export_to_response(job)

    def get_export_job(self, principal: Principal, job_id: UUID) -> ExportJobResponse:
        with tenant_session(self.db, principal.organization_id):
            job = self._get_export_or_404(principal, job_id)
            return self._export_to_response(job)

    def get_export_download(self, principal: Principal, job_id: UUID) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            job = self._get_export_or_404(principal, job_id)
            if job.status != "completed" or not job.result_summary:
                raise AppError(
                    code="EXPORT_NOT_READY",
                    message_key="errors.validation_failed",
                    status_code=409,
                )
            return job.result_summary

    def execute_export_job(self, job_id: UUID, principal: Principal) -> None:
        with tenant_session(self.db, principal.organization_id):
            job = self._get_export_or_404(principal, job_id)
            job.status = "running"
            self.db.flush()
            try:
                bundle = self._build_export_bundle(principal, job)
                job.status = "completed"
                job.result_summary = bundle
                job.storage_key = f"exports/{job.id}.json"
                job.completed_at = datetime.now(tz=UTC)
                self._notify(
                    principal,
                    user_id=principal.user_id,
                    title="Export ready",
                    body=f"Data export {job.id} completed successfully.",
                    link_path=f"/dashboard?export={job.id}",
                )
                self.audit.record(
                    action="export.complete",
                    organization_id=principal.organization_id,
                    actor_user_id=principal.user_id,
                    resource_type="export_job",
                    resource_id=job.id,
                )
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(tz=UTC)
                raise

    def list_erasure_requests(self, principal: Principal) -> list[ErasureRequestResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(ErasureRequest)
                .filter(
                    ErasureRequest.organization_id == principal.organization_id,
                    ErasureRequest.deleted_at.is_(None),
                )
                .order_by(ErasureRequest.created_at.desc())
                .all()
            )
            return [self._erasure_to_response(row) for row in rows]

    def create_erasure_request(
        self, principal: Principal, payload: ErasureRequestCreate
    ) -> ErasureRequestResponse:
        with tenant_session(self.db, principal.organization_id):
            fhir_mapper.get_patient_or_404(self.db, principal.organization_id, payload.patient_id)
            row = ErasureRequest(
                organization_id=principal.organization_id,
                patient_id=payload.patient_id,
                status="pending",
                reason=payload.reason,
                requested_by=principal.user_id,
                data_classification=DataClassification.INTERNAL.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(row)
            self.db.flush()
            self.audit.record(
                action="erasure.request",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="erasure_request",
                resource_id=row.id,
            )
            return self._erasure_to_response(row)

    def review_erasure_request(
        self, principal: Principal, request_id: UUID, payload: ErasureReviewRequest
    ) -> ErasureRequestResponse:
        with tenant_session(self.db, principal.organization_id):
            row = self._get_erasure_or_404(principal, request_id)
            if row.status != "pending":
                raise AppError(code="ERASURE_INVALID_STATE", message_key="errors.validation_failed", status_code=409)
            if payload.decision == "approved":
                row.status = "approved"
            else:
                row.status = "rejected"
            row.reviewed_by = principal.user_id
            row.reviewed_at = datetime.now(tz=UTC)
            self.db.flush()
            self.audit.record(
                action=f"erasure.{payload.decision}",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="erasure_request",
                resource_id=row.id,
                metadata={"reason": payload.reason},
            )
            return self._erasure_to_response(row)

    def complete_erasure_request(self, principal: Principal, request_id: UUID) -> ErasureRequestResponse:
        with tenant_session(self.db, principal.organization_id):
            row = self._get_erasure_or_404(principal, request_id)
            if row.status != "approved":
                raise AppError(code="ERASURE_NOT_APPROVED", message_key="errors.validation_failed", status_code=409)
            patient = fhir_mapper.get_patient_or_404(self.db, principal.organization_id, row.patient_id)
            now = datetime.now(tz=UTC)
            patient.status = "erased"
            patient.deleted_at = now
            patient.given_name = "[erased]"
            patient.family_name = "[erased]"
            patient.contact = None
            patient.national_id = None
            row.status = "completed"
            row.completed_at = now
            self.db.flush()
            self.audit.record(
                action="erasure.complete",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="erasure_request",
                resource_id=row.id,
            )
            self._notify(
                principal,
                user_id=row.requested_by,
                title="Erasure completed",
                body=f"Patient erasure request {row.id} has been completed.",
                link_path="/governance",
            )
            return self._erasure_to_response(row)

    def list_notifications(self, principal: Principal) -> list[NotificationResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(Notification)
                .filter(
                    Notification.organization_id == principal.organization_id,
                    Notification.user_id == principal.user_id,
                    Notification.deleted_at.is_(None),
                )
                .order_by(Notification.created_at.desc())
                .limit(50)
                .all()
            )
            return [self._notification_to_response(row) for row in rows]

    def mark_notification_read(self, principal: Principal, notification_id: UUID) -> NotificationResponse:
        with tenant_session(self.db, principal.organization_id):
            row = (
                self.db.query(Notification)
                .filter(
                    Notification.id == notification_id,
                    Notification.organization_id == principal.organization_id,
                    Notification.user_id == principal.user_id,
                    Notification.deleted_at.is_(None),
                )
                .one_or_none()
            )
            if row is None:
                raise AppError(code="NOTIFICATION_NOT_FOUND", message_key="errors.validation_failed", status_code=404)
            row.is_read = True
            self.db.flush()
            return self._notification_to_response(row)

    def ensure_retention_policies(self, principal: Principal) -> list[RetentionPolicyResponse]:
        with tenant_session(self.db, principal.organization_id):
            existing = {
                row.resource_type
                for row in self.db.query(RetentionPolicy)
                .filter(
                    RetentionPolicy.organization_id == principal.organization_id,
                    RetentionPolicy.deleted_at.is_(None),
                )
                .all()
            }
            for resource_type, days in DEFAULT_RETENTION.items():
                if resource_type in existing:
                    continue
                self.db.add(
                    RetentionPolicy(
                        organization_id=principal.organization_id,
                        resource_type=resource_type,
                        retention_days=days,
                        erasure_enabled=True,
                        data_classification=DataClassification.INTERNAL.value,
                        created_by=principal.user_id,
                        updated_by=principal.user_id,
                    )
                )
            self.db.flush()
            return self.list_retention_policies(principal)

    def list_retention_policies(self, principal: Principal) -> list[RetentionPolicyResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(RetentionPolicy)
                .filter(
                    RetentionPolicy.organization_id == principal.organization_id,
                    RetentionPolicy.deleted_at.is_(None),
                )
                .order_by(RetentionPolicy.resource_type.asc())
                .all()
            )
            return [self._retention_to_response(row) for row in rows]

    def update_retention_policy(
        self, principal: Principal, resource_type: str, payload: RetentionPolicyUpdateRequest
    ) -> RetentionPolicyResponse:
        with tenant_session(self.db, principal.organization_id):
            row = (
                self.db.query(RetentionPolicy)
                .filter(
                    RetentionPolicy.organization_id == principal.organization_id,
                    RetentionPolicy.resource_type == resource_type,
                    RetentionPolicy.deleted_at.is_(None),
                )
                .one_or_none()
            )
            if row is None:
                raise AppError(code="RETENTION_NOT_FOUND", message_key="errors.validation_failed", status_code=404)
            row.retention_days = payload.retention_days
            row.erasure_enabled = payload.erasure_enabled
            row.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="retention.update",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="retention_policy",
                resource_id=row.id,
            )
            return self._retention_to_response(row)

    def governance_dashboard(self, principal: Principal) -> GovernanceDashboardResponse:
        governance = GovernanceService(self.db)
        governance.ensure_default_flags(principal)
        with tenant_session(self.db, principal.organization_id):
            flags = governance.list_flags(principal)
            pending_ai = (
                self.db.query(func.count(AISuggestion.id))
                .filter(
                    AISuggestion.organization_id == principal.organization_id,
                    AISuggestion.decision_status == "pending",
                    AISuggestion.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
            eval_runs = (
                self.db.query(EvalRun)
                .order_by(EvalRun.created_at.desc())
                .limit(5)
                .all()
            )
            policies = self.ensure_retention_policies(principal)
            return GovernanceDashboardResponse(
                feature_flags=[
                    {"key": row.key, "enabled": row.enabled, "description": row.description} for row in flags
                ],
                pending_ai_suggestions=pending_ai,
                recent_eval_runs=[
                    {
                        "id": str(run.id),
                        "passed_gates": run.passed_gates,
                        "metrics": run.metrics,
                        "created_at": run.created_at.isoformat(),
                    }
                    for run in eval_runs
                ],
                retention_policies=policies,
            )

    def _build_export_bundle(self, principal: Principal, job: ExportJob) -> dict[str, Any]:
        org_id = principal.organization_id
        if job.scope == "patient" and job.patient_id is not None:
            patient = fhir_mapper.get_patient_or_404(self.db, org_id, job.patient_id)
            allergies = (
                self.db.query(Allergy)
                .filter(Allergy.patient_id == patient.id, Allergy.organization_id == org_id)
                .all()
            )
            medications = (
                self.db.query(Medication)
                .filter(Medication.patient_id == patient.id, Medication.organization_id == org_id)
                .all()
            )
            history = (
                self.db.query(MedicalHistoryEntry)
                .filter(MedicalHistoryEntry.patient_id == patient.id, MedicalHistoryEntry.organization_id == org_id)
                .all()
            )
            return {
                "export_version": "1.0",
                "scope": "patient",
                "patient": {
                    "id": str(patient.id),
                    "mrn": patient.mrn,
                    "given_name": patient.given_name,
                    "family_name": patient.family_name,
                    "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                },
                "allergies": [{"substance": a.substance_name, "reaction": a.reaction} for a in allergies],
                "medications": [{"drug": m.drug_name, "dose": m.dose} for m in medications],
                "history": [{"category": h.category, "description": h.description} for h in history],
                "fhir_patient": fhir_mapper.patient_to_fhir(patient),
            }

        patients = (
            self.db.query(Patient)
            .filter(Patient.organization_id == org_id, Patient.deleted_at.is_(None))
            .limit(500)
            .all()
        )
        return {
            "export_version": "1.0",
            "scope": "organization",
            "patient_count": len(patients),
            "patients": [
                {"id": str(p.id), "mrn": p.mrn, "name": f"{p.given_name} {p.family_name}"} for p in patients
            ],
        }

    def _render_report_html(
        self,
        *,
        locale: str,
        dir_attr: str,
        patient: Patient,
        problems: list[Problem],
        allergies: list[Allergy],
        note: ClinicalNote | None,
    ) -> str:
        problem_items = "".join(f"<li>{p.description}</li>" for p in problems) or "<li>—</li>"
        allergy_items = "".join(f"<li>{a.substance_name}</li>" for a in allergies) or "<li>—</li>"
        note_section = ""
        if note is not None:
            sections = note.content or {}
            note_section = f"""
            <h2>Note</h2>
            <pre>{json.dumps(sections, ensure_ascii=False, indent=2)}</pre>
            """
        return f"""<!DOCTYPE html>
<html lang="{locale}" dir="{dir_attr}">
<head><meta charset="utf-8"><title>{REPORT_TITLES.get(locale, "Report")}</title></head>
<body>
  <h1>{REPORT_TITLES.get(locale, "Report")}</h1>
  <p><strong>{patient.given_name} {patient.family_name}</strong> · MRN {patient.mrn}</p>
  <h2>Problems</h2><ul>{problem_items}</ul>
  <h2>Allergies</h2><ul>{allergy_items}</ul>
  {note_section}
  <footer><small>AI Examinator — physician-reviewed data only</small></footer>
</body>
</html>"""

    def _notify(
        self,
        principal: Principal,
        *,
        user_id: UUID,
        title: str,
        body: str,
        link_path: str | None,
    ) -> None:
        self.db.add(
            Notification(
                organization_id=principal.organization_id,
                user_id=user_id,
                channel="in_app",
                title=title,
                body=body,
                link_path=link_path,
                email_sent=False,
                data_classification=DataClassification.INTERNAL.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
        )

    def _get_report_or_404(self, principal: Principal, report_id: UUID) -> ClinicalReport:
        report = (
            self.db.query(ClinicalReport)
            .filter(
                ClinicalReport.id == report_id,
                ClinicalReport.organization_id == principal.organization_id,
                ClinicalReport.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if report is None:
            raise AppError(code="REPORT_NOT_FOUND", message_key="errors.validation_failed", status_code=404)
        return report

    def _get_export_or_404(self, principal: Principal, job_id: UUID) -> ExportJob:
        job = (
            self.db.query(ExportJob)
            .filter(
                ExportJob.id == job_id,
                ExportJob.organization_id == principal.organization_id,
                ExportJob.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if job is None:
            raise AppError(code="EXPORT_NOT_FOUND", message_key="errors.validation_failed", status_code=404)
        return job

    def _get_erasure_or_404(self, principal: Principal, request_id: UUID) -> ErasureRequest:
        row = (
            self.db.query(ErasureRequest)
            .filter(
                ErasureRequest.id == request_id,
                ErasureRequest.organization_id == principal.organization_id,
                ErasureRequest.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if row is None:
            raise AppError(code="ERASURE_NOT_FOUND", message_key="errors.validation_failed", status_code=404)
        return row

    @staticmethod
    def _lab_to_response(row: LabImagingResult) -> LabImagingResponse:
        return LabImagingResponse(
            id=row.id,
            patient_id=row.patient_id,
            encounter_id=row.encounter_id,
            result_type=row.result_type,
            loinc_code=row.loinc_code,
            code_display=row.code_display,
            value=row.value,
            unit=row.unit,
            dicom_study_uid=row.dicom_study_uid,
            status=row.status,
            observed_at=row.observed_at,
        )

    @staticmethod
    def _report_to_response(row: ClinicalReport) -> ReportResponse:
        return ReportResponse(
            id=row.id,
            patient_id=row.patient_id,
            session_id=row.session_id,
            locale=row.locale,
            format=row.format,
            title=row.title,
            body_html=row.body_html,
            report_metadata=row.report_metadata,
        )

    @staticmethod
    def _export_to_response(row: ExportJob) -> ExportJobResponse:
        return ExportJobResponse(
            id=row.id,
            patient_id=row.patient_id,
            scope=row.scope,
            status=row.status,
            requested_by=row.requested_by,
            result_summary=row.result_summary,
            error_message=row.error_message,
            completed_at=row.completed_at,
            created_at=row.created_at,
        )

    @staticmethod
    def _erasure_to_response(row: ErasureRequest) -> ErasureRequestResponse:
        return ErasureRequestResponse(
            id=row.id,
            patient_id=row.patient_id,
            status=row.status,
            reason=row.reason,
            requested_by=row.requested_by,
            reviewed_by=row.reviewed_by,
            reviewed_at=row.reviewed_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
        )

    @staticmethod
    def _notification_to_response(row: Notification) -> NotificationResponse:
        return NotificationResponse(
            id=row.id,
            title=row.title,
            body=row.body,
            link_path=row.link_path,
            is_read=row.is_read,
            channel=row.channel,
            created_at=row.created_at,
        )

    @staticmethod
    def _retention_to_response(row: RetentionPolicy) -> RetentionPolicyResponse:
        return RetentionPolicyResponse(
            id=row.id,
            resource_type=row.resource_type,
            retention_days=row.retention_days,
            erasure_enabled=row.erasure_enabled,
        )
