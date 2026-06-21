from uuid import UUID

from sqlalchemy.orm import Session

from app.core.models import Permission, Role, RolePermission, UserRole


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_permissions(self, *, user_id: UUID, organization_id: UUID) -> set[str]:
        rows = (
            self.db.query(Permission.key)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id, UserRole.organization_id == organization_id)
            .all()
        )
        return {row[0] for row in rows}

    def assign_role(
        self,
        *,
        user_id: UUID,
        role_id: UUID,
        organization_id: UUID,
        clinic_id: UUID | None,
        created_by: UUID,
    ) -> UserRole:
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            clinic_id=clinic_id,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def list_roles(self, organization_id: UUID) -> list[Role]:
        return (
            self.db.query(Role)
            .filter((Role.organization_id == organization_id) | (Role.organization_id.is_(None)))
            .order_by(Role.key.asc())
            .all()
        )
