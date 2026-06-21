from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.dependencies import compute_record_hash
from app.core.models import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _latest_hash(self, organization_id: UUID | None) -> str | None:
        latest = (
            self.db.query(AuditLog)
            .filter(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        return latest.record_hash if latest else None

    def record(
        self,
        *,
        action: str,
        organization_id: UUID | None,
        actor_user_id: UUID | None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_hash: str | None = None,
    ) -> AuditLog:
        prev_hash = self._latest_hash(organization_id)
        payload = {
            "action": action,
            "organization_id": str(organization_id) if organization_id else None,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "metadata": metadata or {},
            "ip_hash": ip_hash,
        }
        record = AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata or {},
            ip_hash=ip_hash,
            prev_hash=prev_hash,
            record_hash=compute_record_hash(prev_hash, payload),
        )
        self.db.add(record)
        self.db.flush()
        return record
