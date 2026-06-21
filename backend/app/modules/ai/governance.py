from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.tenant import Principal
from app.modules.ai.models import FeatureFlag

DEFAULT_FLAGS: dict[str, str] = {
    "ai_extraction": "Structured clinical information extraction",
    "ai_suggestions": "DDx, missing questions, exams, and next-step suggestions",
    "ai_draft_note": "AI-generated draft clinical note suggestions",
    "ai_red_flags": "High-sensitivity red-flag detection",
}


class GovernanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_default_flags(self, principal: Principal) -> None:
        with tenant_session(self.db, principal.organization_id):
            existing = {
                row.key
                for row in self.db.query(FeatureFlag)
                .filter(
                    FeatureFlag.organization_id == principal.organization_id,
                    FeatureFlag.deleted_at.is_(None),
                )
                .all()
            }
            for key, description in DEFAULT_FLAGS.items():
                if key in existing:
                    continue
                self.db.add(
                    FeatureFlag(
                        organization_id=principal.organization_id,
                        key=key,
                        enabled=True,
                        description=description,
                        data_classification=DataClassification.INTERNAL.value,
                        created_by=principal.user_id,
                        updated_by=principal.user_id,
                    )
                )
            self.db.flush()

    def is_enabled(self, principal: Principal, key: str) -> bool:
        with tenant_session(self.db, principal.organization_id):
            row = (
                self.db.query(FeatureFlag)
                .filter(
                    FeatureFlag.organization_id == principal.organization_id,
                    FeatureFlag.key == key,
                    FeatureFlag.deleted_at.is_(None),
                )
                .one_or_none()
            )
            if row is None:
                return True
            return row.enabled

    def list_flags(self, principal: Principal) -> list[FeatureFlag]:
        self.ensure_default_flags(principal)
        with tenant_session(self.db, principal.organization_id):
            return (
                self.db.query(FeatureFlag)
                .filter(
                    FeatureFlag.organization_id == principal.organization_id,
                    FeatureFlag.deleted_at.is_(None),
                )
                .order_by(FeatureFlag.key.asc())
                .all()
            )
