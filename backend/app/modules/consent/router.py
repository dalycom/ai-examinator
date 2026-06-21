from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.consent.service import ConsentCaptureRequest, ConsentResponse, ConsentService

router = APIRouter(tags=["consent"])


@router.post("/patients/{patient_id}/consents", response_model=ConsentResponse, status_code=201)
def capture_consent(
    patient_id: UUID,
    payload: ConsentCaptureRequest,
    principal: Principal = Depends(require_permission("consent:capture")),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    service = ConsentService(db)
    result = service.capture_consent(principal, patient_id, payload)
    db.commit()
    return result


@router.get("/patients/{patient_id}/consents", response_model=list[ConsentResponse])
def list_consents(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[ConsentResponse]:
    return ConsentService(db).list_consents(principal, patient_id)


@router.post("/consents/{consent_id}:revoke", response_model=ConsentResponse)
def revoke_consent(
    consent_id: UUID,
    principal: Principal = Depends(require_permission("consent:capture")),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    service = ConsentService(db)
    result = service.revoke_consent(principal, consent_id)
    db.commit()
    return result
