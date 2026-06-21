from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, tenant_session
from app.core.dependencies import require_permission
from app.core.models import AuditLog
from app.core.tenant import Principal

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None
    resource_type: str | None
    resource_id: UUID | None
    metadata: dict[str, Any] | None
    prev_hash: str | None
    record_hash: str
    created_at: datetime


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    with tenant_session(db, principal.organization_id):
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.organization_id == principal.organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            AuditLogResponse(
                id=row.id,
                action=row.action,
                actor_user_id=row.actor_user_id,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                metadata=row.metadata_json,
                prev_hash=row.prev_hash,
                record_hash=row.record_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]
