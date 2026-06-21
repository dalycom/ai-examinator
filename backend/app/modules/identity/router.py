from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.identity.service import (
    ClinicCreateRequest,
    ClinicResponse,
    IdentityService,
    UserCreateRequest,
    UserResponse,
)
from app.modules.rbac.service import PermissionService

router = APIRouter(tags=["identity"])


class AssignRoleRequest(BaseModel):
    role_id: UUID
    clinic_id: UUID | None = None


class RoleResponse(BaseModel):
    id: UUID
    key: str
    name: str
    is_system: bool


@router.get("/clinics", response_model=list[ClinicResponse])
def list_clinics(
    principal: Principal = Depends(require_permission("clinic:read")),
    db: Session = Depends(get_db),
) -> list[ClinicResponse]:
    return IdentityService(db).list_clinics(principal)


@router.post("/clinics", response_model=ClinicResponse, status_code=201)
def create_clinic(
    payload: ClinicCreateRequest,
    principal: Principal = Depends(require_permission("clinic:manage")),
    db: Session = Depends(get_db),
) -> ClinicResponse:
    service = IdentityService(db)
    clinic = service.create_clinic(principal, payload)
    db.commit()
    return clinic


@router.get("/clinics/{clinic_id}", response_model=ClinicResponse)
def get_clinic(
    clinic_id: UUID,
    principal: Principal = Depends(require_permission("clinic:read")),
    db: Session = Depends(get_db),
) -> ClinicResponse:
    return IdentityService(db).get_clinic(principal, clinic_id)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    principal: Principal = Depends(require_permission("user:read")),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    return IdentityService(db).list_users(principal)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreateRequest,
    principal: Principal = Depends(require_permission("user:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    service = IdentityService(db)
    user = service.create_user(principal, payload)
    db.commit()
    return user


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    principal: Principal = Depends(require_permission("role:read")),
    db: Session = Depends(get_db),
) -> list[RoleResponse]:
    roles = PermissionService(db).list_roles(principal.organization_id)
    return [RoleResponse(id=role.id, key=role.key, name=role.name, is_system=role.is_system) for role in roles]


@router.post("/users/{user_id}/roles", status_code=204)
def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    principal: Principal = Depends(require_permission("role:assign")),
    db: Session = Depends(get_db),
) -> None:
    PermissionService(db).assign_role(
        user_id=user_id,
        role_id=payload.role_id,
        organization_id=principal.organization_id,
        clinic_id=payload.clinic_id,
        created_by=principal.user_id,
    )
    db.commit()
