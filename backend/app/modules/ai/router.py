from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.ai.governance import GovernanceService
from app.modules.ai.schemas import (
    FactsListResponse,
    ProvenanceBlock,
    SuggestionDecisionRequest,
    SuggestionResponse,
    SuggestionsListResponse,
    SummaryResponse,
)
from app.modules.ai.service import AIService

router = APIRouter(tags=["ai"])


class FeatureFlagResponse(BaseModel):
    key: str
    enabled: bool
    description: str | None


@router.post("/sessions/{session_id}/extract", response_model=FactsListResponse)
def extract_session(
    session_id: UUID,
    principal: Principal = Depends(require_permission("ai:run")),
    db: Session = Depends(get_db),
) -> FactsListResponse:
    service = AIService(db)
    service.enqueue_extraction(principal, session_id)
    db.commit()
    return service.get_facts(principal, session_id)


@router.get("/sessions/{session_id}/facts", response_model=FactsListResponse)
def get_facts(
    session_id: UUID,
    principal: Principal = Depends(require_permission("ai:read")),
    db: Session = Depends(get_db),
) -> FactsListResponse:
    return AIService(db).get_facts(principal, session_id)


@router.get("/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(
    session_id: UUID,
    principal: Principal = Depends(require_permission("ai:read")),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    return AIService(db).get_summary(principal, session_id)


@router.get("/sessions/{session_id}/suggestions", response_model=SuggestionsListResponse)
def get_suggestions(
    session_id: UUID,
    principal: Principal = Depends(require_permission("ai:read")),
    db: Session = Depends(get_db),
) -> SuggestionsListResponse:
    return AIService(db).get_suggestions(principal, session_id)


@router.post("/suggestions/{suggestion_id}/decision", response_model=SuggestionResponse)
def decide_suggestion(
    suggestion_id: UUID,
    payload: SuggestionDecisionRequest,
    principal: Principal = Depends(require_permission("ai:review")),
    db: Session = Depends(get_db),
) -> SuggestionResponse:
    service = AIService(db)
    result = service.decide_suggestion(principal, suggestion_id, payload)
    db.commit()
    return result


@router.get("/suggestions/{suggestion_id}/provenance", response_model=ProvenanceBlock)
def get_suggestion_provenance(
    suggestion_id: UUID,
    principal: Principal = Depends(require_permission("ai:read")),
    db: Session = Depends(get_db),
) -> ProvenanceBlock:
    return AIService(db).get_provenance(principal, suggestion_id)


@router.get("/governance/feature-flags", response_model=list[FeatureFlagResponse])
def list_feature_flags(
    principal: Principal = Depends(require_permission("governance:manage")),
    db: Session = Depends(get_db),
) -> list[FeatureFlagResponse]:
    service = GovernanceService(db)
    service.ensure_default_flags(principal)
    db.commit()
    rows = service.list_flags(principal)
    return [
        FeatureFlagResponse(key=row.key, enabled=row.enabled, description=row.description) for row in rows
    ]
