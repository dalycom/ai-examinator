from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.audit.service import AuditService
from app.modules.clinical.models import (
    Allergy,
    MedicalHistoryEntry,
    Medication,
    Patient,
    Problem,
    VitalSign,
)


class PatientCreateRequest(BaseModel):
    clinic_id: UUID | None = None
    given_name: str = Field(min_length=1, max_length=128)
    family_name: str = Field(min_length=1, max_length=128)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=16)
    contact: dict[str, Any] | None = None
    preferred_locale: str = "en"


class PatientUpdateRequest(BaseModel):
    given_name: str | None = Field(default=None, max_length=128)
    family_name: str | None = Field(default=None, max_length=128)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=16)
    contact: dict[str, Any] | None = None
    preferred_locale: str | None = None
    status: str | None = None


class PatientResponse(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    date_of_birth: date | None
    sex: str | None
    contact: dict[str, Any] | None
    preferred_locale: str
    status: str
    clinic_id: UUID | None


class AllergyCreateRequest(BaseModel):
    substance_code: str | None = None
    substance_name: str
    reaction: str | None = None
    severity: str | None = None


class MedicationCreateRequest(BaseModel):
    drug_code: str | None = None
    drug_name: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class HistoryCreateRequest(BaseModel):
    category: str = Field(pattern=r"^(medical|surgical|family|social)$")
    description: str
    onset_date: date | None = None


class ProblemCreateRequest(BaseModel):
    icd10_code: str | None = None
    description: str
    onset_date: date | None = None
    encounter_id: UUID | None = None


class VitalCreateRequest(BaseModel):
    encounter_id: UUID | None = None
    loinc_code: str | None = None
    vital_type: str
    value: str
    unit: str | None = None
    measured_at: datetime | None = None


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_patients(self, principal: Principal) -> list[PatientResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(Patient)
                .filter(Patient.organization_id == principal.organization_id, Patient.deleted_at.is_(None))
                .order_by(Patient.family_name.asc(), Patient.given_name.asc())
                .all()
            )
            return [self._to_response(row) for row in rows]

    def create_patient(self, principal: Principal, payload: PatientCreateRequest) -> PatientResponse:
        with tenant_session(self.db, principal.organization_id):
            count = self.db.query(Patient).filter(Patient.organization_id == principal.organization_id).count()
            patient = Patient(
                organization_id=principal.organization_id,
                clinic_id=payload.clinic_id,
                mrn=f"MRN-{count + 1:06d}",
                given_name=payload.given_name,
                family_name=payload.family_name,
                date_of_birth=payload.date_of_birth,
                sex=payload.sex,
                contact=payload.contact,
                preferred_locale=payload.preferred_locale,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(patient)
            self.db.flush()
            self.audit.record(
                action="patient.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="patient",
                resource_id=patient.id,
            )
            return self._to_response(patient)

    def get_patient(self, principal: Principal, patient_id: UUID) -> PatientResponse:
        patient = self._get_patient_or_404(principal, patient_id)
        return self._to_response(patient)

    def update_patient(
        self, principal: Principal, patient_id: UUID, payload: PatientUpdateRequest
    ) -> PatientResponse:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            for field in ("given_name", "family_name", "date_of_birth", "sex", "contact", "preferred_locale", "status"):
                value = getattr(payload, field)
                if value is not None:
                    setattr(patient, field, value)
            patient.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="patient.update",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="patient",
                resource_id=patient.id,
            )
            return self._to_response(patient)

    def add_allergy(self, principal: Principal, patient_id: UUID, payload: AllergyCreateRequest) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            allergy = Allergy(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                substance_code=payload.substance_code,
                substance_name=payload.substance_name,
                reaction=payload.reaction,
                severity=payload.severity,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(allergy)
            self.db.flush()
            return {"id": str(allergy.id), "substance_name": allergy.substance_name}

    def list_allergies(self, principal: Principal, patient_id: UUID) -> list[dict[str, Any]]:
        with tenant_session(self.db, principal.organization_id):
            self._get_patient_or_404(principal, patient_id)
            rows = (
                self.db.query(Allergy)
                .filter(
                    Allergy.organization_id == principal.organization_id,
                    Allergy.patient_id == patient_id,
                    Allergy.deleted_at.is_(None),
                )
                .all()
            )
            return [
                {
                    "id": str(row.id),
                    "substance_code": row.substance_code,
                    "substance_name": row.substance_name,
                    "reaction": row.reaction,
                    "severity": row.severity,
                    "status": row.status,
                }
                for row in rows
            ]

    def add_medication(
        self, principal: Principal, patient_id: UUID, payload: MedicationCreateRequest
    ) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            medication = Medication(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                drug_code=payload.drug_code,
                drug_name=payload.drug_name,
                dose=payload.dose,
                route=payload.route,
                frequency=payload.frequency,
                start_date=payload.start_date,
                end_date=payload.end_date,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(medication)
            self.db.flush()
            return {"id": str(medication.id), "drug_name": medication.drug_name}

    def list_medications(self, principal: Principal, patient_id: UUID) -> list[dict[str, Any]]:
        with tenant_session(self.db, principal.organization_id):
            self._get_patient_or_404(principal, patient_id)
            rows = (
                self.db.query(Medication)
                .filter(
                    Medication.organization_id == principal.organization_id,
                    Medication.patient_id == patient_id,
                    Medication.deleted_at.is_(None),
                )
                .all()
            )
            return [
                {
                    "id": str(row.id),
                    "drug_code": row.drug_code,
                    "drug_name": row.drug_name,
                    "dose": row.dose,
                    "status": row.status,
                }
                for row in rows
            ]

    def add_history(
        self, principal: Principal, patient_id: UUID, payload: HistoryCreateRequest
    ) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            entry = MedicalHistoryEntry(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                category=payload.category,
                description=payload.description,
                onset_date=payload.onset_date,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(entry)
            self.db.flush()
            return {"id": str(entry.id), "category": entry.category}

    def list_history(self, principal: Principal, patient_id: UUID) -> list[dict[str, Any]]:
        with tenant_session(self.db, principal.organization_id):
            self._get_patient_or_404(principal, patient_id)
            rows = (
                self.db.query(MedicalHistoryEntry)
                .filter(
                    MedicalHistoryEntry.organization_id == principal.organization_id,
                    MedicalHistoryEntry.patient_id == patient_id,
                    MedicalHistoryEntry.deleted_at.is_(None),
                )
                .all()
            )
            return [
                {
                    "id": str(row.id),
                    "category": row.category,
                    "description": row.description,
                    "onset_date": row.onset_date.isoformat() if row.onset_date else None,
                }
                for row in rows
            ]

    def add_problem(self, principal: Principal, patient_id: UUID, payload: ProblemCreateRequest) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            problem = Problem(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                encounter_id=payload.encounter_id,
                icd10_code=payload.icd10_code,
                description=payload.description,
                onset_date=payload.onset_date,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(problem)
            self.db.flush()
            return {"id": str(problem.id), "description": problem.description}

    def add_vital(self, principal: Principal, patient_id: UUID, payload: VitalCreateRequest) -> dict[str, Any]:
        with tenant_session(self.db, principal.organization_id):
            patient = self._get_patient_or_404(principal, patient_id)
            vital = VitalSign(
                organization_id=principal.organization_id,
                patient_id=patient.id,
                encounter_id=payload.encounter_id,
                loinc_code=payload.loinc_code,
                vital_type=payload.vital_type,
                value=payload.value,
                unit=payload.unit,
                measured_at=payload.measured_at or datetime.now(),
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(vital)
            self.db.flush()
            return {"id": str(vital.id), "vital_type": vital.vital_type, "value": vital.value}

    def _get_patient_or_404(self, principal: Principal, patient_id: UUID) -> Patient:
        with tenant_session(self.db, principal.organization_id):
            patient = self.db.get(Patient, patient_id)
            if (
                patient is None
                or patient.organization_id != principal.organization_id
                or patient.deleted_at is not None
            ):
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            return patient

    @staticmethod
    def _to_response(patient: Patient) -> PatientResponse:
        return PatientResponse(
            id=patient.id,
            mrn=patient.mrn,
            given_name=patient.given_name,
            family_name=patient.family_name,
            date_of_birth=patient.date_of_birth,
            sex=patient.sex,
            contact=patient.contact,
            preferred_locale=patient.preferred_locale,
            status=patient.status,
            clinic_id=patient.clinic_id,
        )
