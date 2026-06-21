from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.patients.service import (
    AllergyCreateRequest,
    HistoryCreateRequest,
    MedicationCreateRequest,
    PatientCreateRequest,
    PatientResponse,
    PatientService,
    PatientUpdateRequest,
    ProblemCreateRequest,
    VitalCreateRequest,
)

router = APIRouter(tags=["patients"])


@router.get("/patients", response_model=list[PatientResponse])
def list_patients(
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[PatientResponse]:
    return PatientService(db).list_patients(principal)


@router.post("/patients", response_model=PatientResponse, status_code=201)
def create_patient(
    payload: PatientCreateRequest,
    principal: Principal = Depends(require_permission("patient:create")),
    db: Session = Depends(get_db),
) -> PatientResponse:
    service = PatientService(db)
    patient = service.create_patient(principal, payload)
    db.commit()
    return patient


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> PatientResponse:
    return PatientService(db).get_patient(principal, patient_id)


@router.patch("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> PatientResponse:
    service = PatientService(db)
    patient = service.update_patient(principal, patient_id, payload)
    db.commit()
    return patient


@router.get("/patients/{patient_id}/allergies")
def list_allergies(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return PatientService(db).list_allergies(principal, patient_id)


@router.post("/patients/{patient_id}/allergies", status_code=201)
def add_allergy(
    patient_id: UUID,
    payload: AllergyCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = PatientService(db).add_allergy(principal, patient_id, payload)
    db.commit()
    return result


@router.get("/patients/{patient_id}/medications")
def list_medications(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return PatientService(db).list_medications(principal, patient_id)


@router.post("/patients/{patient_id}/medications", status_code=201)
def add_medication(
    patient_id: UUID,
    payload: MedicationCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = PatientService(db).add_medication(principal, patient_id, payload)
    db.commit()
    return result


@router.get("/patients/{patient_id}/history")
def list_history(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return PatientService(db).list_history(principal, patient_id)


@router.post("/patients/{patient_id}/history", status_code=201)
def add_history(
    patient_id: UUID,
    payload: HistoryCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = PatientService(db).add_history(principal, patient_id, payload)
    db.commit()
    return result


@router.post("/patients/{patient_id}/problems", status_code=201)
def add_problem(
    patient_id: UUID,
    payload: ProblemCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = PatientService(db).add_problem(principal, patient_id, payload)
    db.commit()
    return result


@router.post("/patients/{patient_id}/vitals", status_code=201)
def add_vital(
    patient_id: UUID,
    payload: VitalCreateRequest,
    principal: Principal = Depends(require_permission("patient:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = PatientService(db).add_vital(principal, patient_id, payload)
    db.commit()
    return result
