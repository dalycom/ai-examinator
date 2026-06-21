from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.core.errors import AppError

ModelT = TypeVar("ModelT")


class TenantScopedRepository[ModelT]:
    def __init__(self, db: Session, organization_id: UUID) -> None:
        self.db = db
        self.organization_id = organization_id

    def scoped_query(self, model: type[ModelT]) -> Query[ModelT]:
        if not hasattr(model, "organization_id"):
            raise AppError(
                code="TENANT_SCOPE_ERROR",
                message_key="errors.http_error",
                status_code=500,
            )
        return self.db.query(model).filter(model.organization_id == self.organization_id)  # type: ignore[attr-defined]

    def assert_same_org(self, entity: ModelT) -> ModelT:
        org_id = getattr(entity, "organization_id", None)
        if org_id != self.organization_id:
            raise AppError(
                code="FORBIDDEN",
                message_key="errors.forbidden",
                status_code=403,
            )
        return entity
