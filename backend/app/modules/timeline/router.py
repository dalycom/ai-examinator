from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.timeline.service import TimelineEvent, TimelineService

router = APIRouter(tags=["timeline"])


@router.get("/patients/{patient_id}/timeline", response_model=list[TimelineEvent])
def get_patient_timeline(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("patient:read")),
    db: Session = Depends(get_db),
) -> list[TimelineEvent]:
    return TimelineService(db).get_patient_timeline(principal, patient_id)
