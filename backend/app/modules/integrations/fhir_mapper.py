from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.clinical.models import Allergy, Encounter, Medication, Patient, Problem, VitalSign
from app.modules.consultation.models import ClinicalNote, ConsultationSession
from app.modules.integrations.models import LabImagingResult


def _fhir_meta(*, last_updated: datetime | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]}
    if last_updated is not None:
        meta["lastUpdated"] = last_updated.isoformat()
    return meta


def patient_to_fhir(patient: Patient) -> dict[str, Any]:
    name = [{"use": "official", "family": patient.family_name, "given": [patient.given_name]}]
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient.id),
        "meta": _fhir_meta(last_updated=patient.updated_at),
        "identifier": [{"system": "urn:ai-examinator:mrn", "value": patient.mrn}],
        "name": name,
        "gender": _map_gender(patient.sex),
        "active": patient.status == "active" and patient.deleted_at is None,
    }
    if patient.date_of_birth is not None:
        resource["birthDate"] = patient.date_of_birth.isoformat()
    if patient.contact:
        telecom = []
        if patient.contact.get("phone"):
            telecom.append({"system": "phone", "value": patient.contact["phone"]})
        if patient.contact.get("email"):
            telecom.append({"system": "email", "value": patient.contact["email"]})
        if telecom:
            resource["telecom"] = telecom
    return resource


def encounter_to_fhir(encounter: Encounter) -> dict[str, Any]:
    return {
        "resourceType": "Encounter",
        "id": str(encounter.id),
        "meta": _fhir_meta(last_updated=encounter.updated_at),
        "status": _map_encounter_status(encounter.status),
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB" if encounter.encounter_type == "outpatient" else "IMP",
        },
        "subject": {"reference": f"Patient/{encounter.patient_id}"},
        "period": {
            "start": encounter.started_at.isoformat(),
            "end": encounter.ended_at.isoformat() if encounter.ended_at else None,
        },
    }


def observation_from_vital(vital: VitalSign) -> dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": str(vital.id),
        "meta": _fhir_meta(last_updated=vital.updated_at),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": vital.loinc_code or "unknown",
                    "display": vital.vital_type,
                }
            ],
            "text": vital.vital_type,
        },
        "subject": {"reference": f"Patient/{vital.patient_id}"},
        "effectiveDateTime": vital.measured_at.isoformat(),
        "valueQuantity": {"value": vital.value, "unit": vital.unit or ""},
    }


def observation_from_lab_result(result: LabImagingResult) -> dict[str, Any]:
    category_code = "laboratory" if result.result_type == "lab" else "imaging"
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "id": str(result.id),
        "meta": _fhir_meta(last_updated=result.updated_at),
        "status": result.status,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": category_code,
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": result.loinc_code or "unknown",
                    "display": result.code_display,
                }
            ],
            "text": result.code_display,
        },
        "subject": {"reference": f"Patient/{result.patient_id}"},
        "effectiveDateTime": result.observed_at.isoformat(),
    }
    if result.value:
        resource["valueString"] = result.value
        if result.unit:
            resource["valueQuantity"] = {"value": result.value, "unit": result.unit}
    if result.dicom_study_uid:
        resource["identifier"] = [
            {"system": "urn:dicom:uid", "value": f"urn:oid:{result.dicom_study_uid}"}
        ]
    return resource


def condition_from_problem(problem: Problem) -> dict[str, Any]:
    coding = []
    if problem.icd10_code:
        coding.append(
            {
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": problem.icd10_code,
                "display": problem.description,
            }
        )
    return {
        "resourceType": "Condition",
        "id": str(problem.id),
        "meta": _fhir_meta(last_updated=problem.updated_at),
        "clinicalStatus": {"coding": [{"code": problem.status}]},
        "code": {"coding": coding, "text": problem.description},
        "subject": {"reference": f"Patient/{problem.patient_id}"},
    }


def allergy_intolerance_from_allergy(allergy: Allergy) -> dict[str, Any]:
    return {
        "resourceType": "AllergyIntolerance",
        "id": str(allergy.id),
        "meta": _fhir_meta(last_updated=allergy.updated_at),
        "clinicalStatus": {"coding": [{"code": allergy.status}]},
        "code": {"text": allergy.substance_name},
        "patient": {"reference": f"Patient/{allergy.patient_id}"},
        "reaction": [{"manifestation": [{"text": allergy.reaction or "unknown"}]}] if allergy.reaction else [],
    }


def medication_statement_from_medication(medication: Medication) -> dict[str, Any]:
    return {
        "resourceType": "MedicationStatement",
        "id": str(medication.id),
        "meta": _fhir_meta(last_updated=medication.updated_at),
        "status": medication.status,
        "medicationCodeableConcept": {"text": medication.drug_name},
        "subject": {"reference": f"Patient/{medication.patient_id}"},
        "dosage": [{"text": medication.dose, "route": {"text": medication.route}}] if medication.dose else [],
    }


def bundle_from_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": [{"resource": entry} for entry in entries],
    }


def get_patient_or_404(db: Session, organization_id: UUID, patient_id: UUID) -> Patient:
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == patient_id,
            Patient.organization_id == organization_id,
            Patient.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if patient is None:
        raise AppError(code="PATIENT_NOT_FOUND", message_key="errors.patient_not_found", status_code=404)
    return patient


def get_encounter_or_404(db: Session, organization_id: UUID, encounter_id: UUID) -> Encounter:
    encounter = (
        db.query(Encounter)
        .filter(
            Encounter.id == encounter_id,
            Encounter.organization_id == organization_id,
            Encounter.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if encounter is None:
        raise AppError(code="ENCOUNTER_NOT_FOUND", message_key="errors.encounter_not_found", status_code=404)
    return encounter


def get_session_or_404(db: Session, organization_id: UUID, session_id: UUID) -> ConsultationSession:
    session = (
        db.query(ConsultationSession)
        .filter(
            ConsultationSession.id == session_id,
            ConsultationSession.organization_id == organization_id,
            ConsultationSession.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if session is None:
        raise AppError(code="SESSION_NOT_FOUND", message_key="errors.session_not_found", status_code=404)
    return session


def get_note_for_session(db: Session, organization_id: UUID, session_id: UUID) -> ClinicalNote | None:
    return (
        db.query(ClinicalNote)
        .filter(
            ClinicalNote.session_id == session_id,
            ClinicalNote.organization_id == organization_id,
            ClinicalNote.deleted_at.is_(None),
        )
        .order_by(ClinicalNote.updated_at.desc())
        .first()
    )


def _map_gender(sex: str | None) -> str:
    match sex:
        case "male":
            return "male"
        case "female":
            return "female"
        case "other":
            return "other"
        case _:
            return "unknown"


def _map_encounter_status(status: str) -> str:
    match status:
        case "in_progress":
            return "in-progress"
        case "completed":
            return "finished"
        case "cancelled":
            return "cancelled"
        case _:
            return "unknown"
