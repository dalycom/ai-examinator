from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.errors import AppError
from app.core.models import Clinic, ClinicMembership, User
from app.core.tenant import Principal
from app.modules.audit.service import AuditService


class ClinicCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    timezone: str = Field(default="UTC", max_length=64)
    address: dict[str, Any] | None = None


class ClinicResponse(BaseModel):
    id: UUID
    name: str
    timezone: str
    status: str
    address: dict[str, Any] | None


class UserCreateRequest(BaseModel):
    email: str
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    preferred_locale: str = "en"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    status: str
    preferred_locale: str


class IdentityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_clinics(self, principal: Principal) -> list[ClinicResponse]:
        with tenant_session(self.db, principal.organization_id):
            clinics = (
                self.db.query(Clinic)
                .filter(
                    Clinic.organization_id == principal.organization_id,
                    Clinic.deleted_at.is_(None),
                )
                .order_by(Clinic.name.asc())
                .all()
            )
            return [self._clinic_to_response(clinic) for clinic in clinics]

    def create_clinic(self, principal: Principal, payload: ClinicCreateRequest) -> ClinicResponse:
        with tenant_session(self.db, principal.organization_id):
            clinic = Clinic(
                organization_id=principal.organization_id,
                name=payload.name,
                timezone=payload.timezone,
                address=payload.address,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(clinic)
            self.db.flush()
            self.audit.record(
                action="clinic.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinic",
                resource_id=clinic.id,
                metadata={"name": clinic.name},
            )
            return self._clinic_to_response(clinic)

    def get_clinic(self, principal: Principal, clinic_id: UUID) -> ClinicResponse:
        with tenant_session(self.db, principal.organization_id):
            clinic = self._get_clinic_or_404(clinic_id, principal.organization_id)
            return self._clinic_to_response(clinic)

    def list_users(self, principal: Principal) -> list[UserResponse]:
        with tenant_session(self.db, principal.organization_id):
            users = (
                self.db.query(User)
                .filter(
                    User.organization_id == principal.organization_id,
                    User.deleted_at.is_(None),
                )
                .order_by(User.full_name.asc())
                .all()
            )
            return [self._user_to_response(user) for user in users]

    def create_user(self, principal: Principal, payload: UserCreateRequest) -> UserResponse:
        from app.core.security import hash_password

        with tenant_session(self.db, principal.organization_id):
            existing = (
                self.db.query(User)
                .filter(
                    User.organization_id == principal.organization_id,
                    User.email == payload.email.lower(),
                )
                .first()
            )
            if existing:
                raise AppError(
                    code="USER_EXISTS",
                    message_key="errors.http_error",
                    status_code=409,
                    details={"email": payload.email},
                )
            user = User(
                organization_id=principal.organization_id,
                email=payload.email.lower(),
                full_name=payload.full_name,
                password_hash=hash_password(payload.password),
                preferred_locale=payload.preferred_locale,
                status="active",
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(user)
            self.db.flush()
            self.audit.record(
                action="user.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="user",
                resource_id=user.id,
            )
            return self._user_to_response(user)

    def add_clinic_membership(
        self, principal: Principal, *, clinic_id: UUID, user_id: UUID, is_primary: bool = False
    ) -> None:
        with tenant_session(self.db, principal.organization_id):
            clinic = self._get_clinic_or_404(clinic_id, principal.organization_id)
            user = self.db.get(User, user_id)
            if user is None or user.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            membership = ClinicMembership(
                organization_id=principal.organization_id,
                clinic_id=clinic.id,
                user_id=user.id,
                is_primary=is_primary,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(membership)
            self.db.flush()
            self.audit.record(
                action="clinic_membership.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinic_membership",
                resource_id=membership.id,
            )

    def _get_clinic_or_404(self, clinic_id: UUID, organization_id: UUID) -> Clinic:
        clinic = self.db.get(Clinic, clinic_id)
        if clinic is None or clinic.organization_id != organization_id or clinic.deleted_at is not None:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return clinic

    @staticmethod
    def _clinic_to_response(clinic: Clinic) -> ClinicResponse:
        return ClinicResponse(
            id=clinic.id,
            name=clinic.name,
            timezone=clinic.timezone,
            status=clinic.status,
            address=clinic.address,
        )

    @staticmethod
    def _user_to_response(user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            preferred_locale=user.preferred_locale,
        )
