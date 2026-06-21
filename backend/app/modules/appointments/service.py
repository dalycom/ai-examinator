from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.audit.service import AuditService
from app.modules.clinical.models import Appointment, Encounter, Patient


class AppointmentCreateRequest(BaseModel):
    patient_id: UUID
    clinic_id: UUID
    clinician_id: UUID
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    clinic_id: UUID
    clinician_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    notes: str | None


class EncounterCreateRequest(BaseModel):
    patient_id: UUID
    clinic_id: UUID
    clinician_id: UUID
    appointment_id: UUID | None = None
    encounter_type: str = Field(default="outpatient", max_length=32)


class EncounterResponse(BaseModel):
    id: UUID
    patient_id: UUID
    clinic_id: UUID
    clinician_id: UUID
    appointment_id: UUID | None
    encounter_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_appointments(self, principal: Principal) -> list[AppointmentResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(Appointment)
                .filter(
                    Appointment.organization_id == principal.organization_id,
                    Appointment.deleted_at.is_(None),
                )
                .order_by(Appointment.starts_at.desc())
                .all()
            )
            return [self._appointment_response(row) for row in rows]

    def create_appointment(self, principal: Principal, payload: AppointmentCreateRequest) -> AppointmentResponse:
        with tenant_session(self.db, principal.organization_id):
            self._assert_patient(principal, payload.patient_id)
            appointment = Appointment(
                organization_id=principal.organization_id,
                patient_id=payload.patient_id,
                clinic_id=payload.clinic_id,
                clinician_id=payload.clinician_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                notes=payload.notes,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(appointment)
            self.db.flush()
            self.audit.record(
                action="appointment.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="appointment",
                resource_id=appointment.id,
            )
            return self._appointment_response(appointment)

    def _assert_patient(self, principal: Principal, patient_id: UUID) -> Patient:
        patient = self.db.get(Patient, patient_id)
        if patient is None or patient.organization_id != principal.organization_id:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return patient

    @staticmethod
    def _appointment_response(row: Appointment) -> AppointmentResponse:
        return AppointmentResponse(
            id=row.id,
            patient_id=row.patient_id,
            clinic_id=row.clinic_id,
            clinician_id=row.clinician_id,
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            status=row.status,
            notes=row.notes,
        )


class EncounterService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def create_encounter(self, principal: Principal, payload: EncounterCreateRequest) -> EncounterResponse:
        with tenant_session(self.db, principal.organization_id):
            patient = self.db.get(Patient, payload.patient_id)
            if patient is None or patient.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            encounter = Encounter(
                organization_id=principal.organization_id,
                patient_id=payload.patient_id,
                clinic_id=payload.clinic_id,
                clinician_id=payload.clinician_id,
                appointment_id=payload.appointment_id,
                encounter_type=payload.encounter_type,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(encounter)
            self.db.flush()
            self.audit.record(
                action="encounter.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="encounter",
                resource_id=encounter.id,
            )
            return self._encounter_response(encounter)

    def get_encounter(self, principal: Principal, encounter_id: UUID) -> EncounterResponse:
        with tenant_session(self.db, principal.organization_id):
            encounter = self.db.get(Encounter, encounter_id)
            if encounter is None or encounter.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            return self._encounter_response(encounter)

    @staticmethod
    def _encounter_response(row: Encounter) -> EncounterResponse:
        return EncounterResponse(
            id=row.id,
            patient_id=row.patient_id,
            clinic_id=row.clinic_id,
            clinician_id=row.clinician_id,
            appointment_id=row.appointment_id,
            encounter_type=row.encounter_type,
            status=row.status,
            started_at=row.started_at,
            ended_at=row.ended_at,
        )
