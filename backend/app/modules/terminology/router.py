from fastapi import APIRouter, Depends, Query

from app.adapters.terminology.stub_adapter import get_terminology_adapter
from app.core.dependencies import require_permission
from app.core.tenant import Principal

router = APIRouter(prefix="/terminology", tags=["terminology"])


@router.get("/icd10")
def lookup_icd10(
    q: str = Query(min_length=1),
    principal: Principal = Depends(require_permission("patient:read")),
) -> list[dict[str, str]]:
    _ = principal
    return get_terminology_adapter().lookup_icd10(q)


@router.get("/rxnorm")
def lookup_rxnorm(
    q: str = Query(min_length=1),
    principal: Principal = Depends(require_permission("patient:read")),
) -> list[dict[str, str]]:
    _ = principal
    return get_terminology_adapter().lookup_rxnorm(q)
