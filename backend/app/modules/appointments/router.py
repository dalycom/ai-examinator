from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.appointments.service import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentService,
    EncounterCreateRequest,
    EncounterResponse,
    EncounterService,
)

router = APIRouter(tags=["appointments"])


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(
    principal: Principal = Depends(require_permission("appointment:read")),
    db: Session = Depends(get_db),
) -> list[AppointmentResponse]:
    return AppointmentService(db).list_appointments(principal)


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
def create_appointment(
    payload: AppointmentCreateRequest,
    principal: Principal = Depends(require_permission("appointment:manage")),
    db: Session = Depends(get_db),
) -> AppointmentResponse:
    service = AppointmentService(db)
    appointment = service.create_appointment(principal, payload)
    db.commit()
    return appointment


@router.post("/encounters", response_model=EncounterResponse, status_code=201)
def create_encounter(
    payload: EncounterCreateRequest,
    principal: Principal = Depends(require_permission("consultation:start")),
    db: Session = Depends(get_db),
) -> EncounterResponse:
    service = EncounterService(db)
    encounter = service.create_encounter(principal, payload)
    db.commit()
    return encounter


@router.get("/encounters/{encounter_id}", response_model=EncounterResponse)
def get_encounter(
    encounter_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> EncounterResponse:
    return EncounterService(db).get_encounter(principal, encounter_id)
