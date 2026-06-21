from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.audit.service import AuditService
from app.modules.clinical.models import Patient
from app.modules.consultation.models import ConsentRecord


class ConsentCaptureRequest(BaseModel):
    scopes: dict[str, bool] = Field(
        description="Consent scopes, e.g. recording=true, ai_processing=true",
    )
    method: str = Field(default="verbal_confirmed", max_length=32)
    encounter_id: UUID | None = None


class ConsentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    scopes: dict[str, Any]
    method: str
    captured_at: datetime
    status: str


class ConsentService:
    REQUIRED_RECORDING_SCOPE = "recording"
    REQUIRED_AI_SCOPE = "ai_processing"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def capture_consent(
        self, principal: Principal, patient_id: UUID, payload: ConsentCaptureRequest
    ) -> ConsentResponse:
        with tenant_session(self.db, principal.organization_id):
            patient = self.db.get(Patient, patient_id)
            if patient is None or patient.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)

            record = ConsentRecord(
                organization_id=principal.organization_id,
                patient_id=patient_id,
                encounter_id=payload.encounter_id,
                scopes=payload.scopes,
                method=payload.method,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(record)
            self.db.flush()
            self.audit.record(
                action="consent.capture",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="consent_record",
                resource_id=record.id,
                metadata={"scopes": payload.scopes, "method": payload.method},
            )
            return self._to_response(record)

    def list_consents(self, principal: Principal, patient_id: UUID) -> list[ConsentResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(ConsentRecord)
                .filter(
                    ConsentRecord.organization_id == principal.organization_id,
                    ConsentRecord.patient_id == patient_id,
                    ConsentRecord.deleted_at.is_(None),
                )
                .order_by(ConsentRecord.captured_at.desc())
                .all()
            )
            return [self._to_response(row) for row in rows]

    def revoke_consent(self, principal: Principal, consent_id: UUID) -> ConsentResponse:
        with tenant_session(self.db, principal.organization_id):
            record = self.db.get(ConsentRecord, consent_id)
            if record is None or record.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            record.status = "revoked"
            record.revoked_at = datetime.now(UTC)
            record.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="consent.revoke",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="consent_record",
                resource_id=record.id,
            )
            return self._to_response(record)

    def require_scope(self, principal: Principal, patient_id: UUID, scope: str) -> None:
        if not self.has_active_scope(principal, patient_id, scope):
            raise AppError(
                code="CONSENT_REQUIRED",
                message_key="errors.consent_required",
                status_code=403,
                details={"scope": scope},
            )

    def has_active_scope(self, principal: Principal, patient_id: UUID, scope: str) -> bool:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(ConsentRecord)
                .filter(
                    ConsentRecord.organization_id == principal.organization_id,
                    ConsentRecord.patient_id == patient_id,
                    ConsentRecord.status == "active",
                    ConsentRecord.deleted_at.is_(None),
                )
                .all()
            )
            return any(row.scopes.get(scope) is True for row in rows)

    @staticmethod
    def _to_response(record: ConsentRecord) -> ConsentResponse:
        return ConsentResponse(
            id=record.id,
            patient_id=record.patient_id,
            encounter_id=record.encounter_id,
            scopes=record.scopes,
            method=record.method,
            captured_at=record.captured_at,
            status=record.status,
        )
