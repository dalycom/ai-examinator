from datetime import UTC, datetime, timedelta
from uuid import UUID

import pyotp
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import bypass_tenant_rls_session, tenant_session
from app.core.enums import Locale
from app.core.errors import AppError
from app.core.models import Organization, RefreshToken, Role, User, UserRole
from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.audit.service import AuditService
from app.modules.rbac.service import PermissionService

settings = get_settings()


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_full_name: str = Field(min_length=2, max_length=255)
    admin_password: str = Field(min_length=12, max_length=128)
    default_locale: Locale = Locale.EN


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=6)


class MfaConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    mfa_required: bool = False
    mfa_token: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    preferred_locale: Locale
    organization_id: UUID
    permissions: list[str]


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.permissions = PermissionService(db)

    def register_organization(
        self,
        payload: RegisterOrganizationRequest,
        *,
        ip_hash: str | None = None,
    ) -> tuple[User, Organization, TokenResponse]:
        existing = self.db.query(Organization).filter(Organization.slug == payload.organization_slug).first()
        if existing:
            raise AppError(
                code="ORGANIZATION_EXISTS",
                message_key="errors.organization_exists",
                status_code=409,
            )

        organization = Organization(
            name=payload.organization_name,
            slug=payload.organization_slug,
            default_locale=payload.default_locale.value,
        )
        self.db.add(organization)
        self.db.flush()

        with tenant_session(self.db, organization.id):
            user = User(
                organization_id=organization.id,
                email=payload.admin_email.lower(),
                full_name=payload.admin_full_name,
                password_hash=hash_password(payload.admin_password),
                preferred_locale=payload.default_locale.value,
                status="active",
                created_by=None,
                updated_by=None,
            )
            self.db.add(user)
            self.db.flush()

            org_admin_role = (
                self.db.query(Role).filter(Role.key == "org_admin", Role.organization_id.is_(None)).one()
            )
            self.db.add(
                UserRole(
                    user_id=user.id,
                    role_id=org_admin_role.id,
                    organization_id=organization.id,
                    created_by=user.id,
                    updated_by=user.id,
                )
            )
            self.db.flush()

            self.audit.record(
                action="auth.register_organization",
                organization_id=organization.id,
                actor_user_id=user.id,
                resource_type="organization",
                resource_id=organization.id,
                metadata={"slug": organization.slug},
                ip_hash=ip_hash,
            )

            tokens = self._issue_tokens(user=user, ip_hash=ip_hash)

        return user, organization, tokens

    def login(self, payload: LoginRequest, *, ip_hash: str | None = None) -> TokenResponse:
        with bypass_tenant_rls_session(self.db):
            user = self.db.query(User).filter(User.email == payload.email.lower()).first()
            if user is None or not verify_password(payload.password, user.password_hash):
                raise AppError(
                    code="INVALID_CREDENTIALS",
                    message_key="errors.invalid_credentials",
                    status_code=401,
                )
            if user.status != "active":
                raise AppError(
                    code="USER_DISABLED",
                    message_key="errors.user_disabled",
                    status_code=403,
                )

            if user.mfa_enabled:
                return TokenResponse(
                    access_token="",  # nosec B106 — MFA challenge defers token issuance
                    expires_in=0,
                    mfa_required=True,
                    mfa_token=create_mfa_challenge_token(user_id=user.id, organization_id=user.organization_id),
                )

            user.last_login_at = datetime.now(UTC)
            with tenant_session(self.db, user.organization_id):
                self.audit.record(
                    action="auth.login",
                    organization_id=user.organization_id,
                    actor_user_id=user.id,
                    resource_type="user",
                    resource_id=user.id,
                    ip_hash=ip_hash,
                )
                return self._issue_tokens(user=user, ip_hash=ip_hash)

    def verify_mfa(self, payload: MfaVerifyRequest, *, ip_hash: str | None = None) -> TokenResponse:
        from app.core.security import decode_token

        try:
            token_payload = decode_token(payload.mfa_token)
        except Exception as exc:
            raise AppError(
                code="UNAUTHORIZED",
                message_key="errors.unauthorized",
                status_code=401,
            ) from exc

        if token_payload.get("type") != "mfa":
            raise AppError(
                code="UNAUTHORIZED",
                message_key="errors.unauthorized",
                status_code=401,
            )

        with bypass_tenant_rls_session(self.db):
            user = self.db.get(User, UUID(token_payload["sub"]))
            if user is None or not user.mfa_enabled or not user.mfa_secret:
                raise AppError(
                    code="MFA_REQUIRED",
                    message_key="errors.mfa_required",
                    status_code=401,
                )

            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(payload.code, valid_window=1):
                raise AppError(
                    code="INVALID_MFA",
                    message_key="errors.invalid_mfa_code",
                    status_code=401,
                )

            user.last_login_at = datetime.now(UTC)
            with tenant_session(self.db, user.organization_id):
                self.audit.record(
                    action="auth.mfa_verify",
                    organization_id=user.organization_id,
                    actor_user_id=user.id,
                    resource_type="user",
                    resource_id=user.id,
                    ip_hash=ip_hash,
                )
                return self._issue_tokens(user=user, ip_hash=ip_hash)

    def refresh(self, payload: RefreshRequest, *, ip_hash: str | None = None) -> TokenResponse:
        token_hash = hash_token(payload.refresh_token)
        with bypass_tenant_rls_session(self.db):
            stored = (
                self.db.query(RefreshToken)
                .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
                .first()
            )
            if stored is None or stored.expires_at < datetime.now(UTC):
                raise AppError(
                    code="REFRESH_INVALID",
                    message_key="errors.refresh_token_invalid",
                    status_code=401,
                )

            user = self.db.get(User, stored.user_id)
            if user is None or user.status != "active":
                raise AppError(
                    code="REFRESH_INVALID",
                    message_key="errors.refresh_token_invalid",
                    status_code=401,
                )

            stored.revoked_at = datetime.now(UTC)
            with tenant_session(self.db, user.organization_id):
                self.audit.record(
                    action="auth.refresh",
                    organization_id=user.organization_id,
                    actor_user_id=user.id,
                    resource_type="user",
                    resource_id=user.id,
                    ip_hash=ip_hash,
                )
                return self._issue_tokens(user=user, ip_hash=ip_hash)

    def logout(self, payload: RefreshRequest, *, user_id: UUID, ip_hash: str | None = None) -> None:
        token_hash = hash_token(payload.refresh_token)
        stored = self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if stored:
            stored.revoked_at = datetime.now(UTC)
        user = self.db.get(User, user_id)
        if user:
            self.audit.record(
                action="auth.logout",
                organization_id=user.organization_id,
                actor_user_id=user.id,
                resource_type="user",
                resource_id=user.id,
                ip_hash=ip_hash,
            )

    def get_me(self, user_id: UUID, organization_id: UUID) -> UserResponse:
        with tenant_session(self.db, organization_id):
            user = self.db.get(User, user_id)
            if user is None or user.organization_id != organization_id:
                raise AppError(
                    code="UNAUTHORIZED",
                    message_key="errors.unauthorized",
                    status_code=401,
                )
            permission_keys = sorted(
                self.permissions.get_user_permissions(user_id=user_id, organization_id=organization_id)
            )
            return UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                preferred_locale=Locale(user.preferred_locale),
                organization_id=user.organization_id,
                permissions=permission_keys,
            )

    def enroll_mfa(self, user_id: UUID) -> dict[str, str]:
        user = self.db.get(User, user_id)
        if user is None:
            raise AppError(
                code="UNAUTHORIZED",
                message_key="errors.unauthorized",
                status_code=401,
            )
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.mfa_enabled = False
        self.db.flush()
        provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=settings.mfa_issuer,
        )
        return {"secret": secret, "provisioning_uri": provisioning_uri}

    def confirm_mfa(self, user_id: UUID, code: str, *, ip_hash: str | None = None) -> None:
        user = self.db.get(User, user_id)
        if user is None or not user.mfa_secret:
            raise AppError(
                code="MFA_REQUIRED",
                message_key="errors.mfa_required",
                status_code=400,
            )
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            raise AppError(
                code="INVALID_MFA",
                message_key="errors.invalid_mfa_code",
                status_code=401,
            )
        user.mfa_enabled = True
        with tenant_session(self.db, user.organization_id):
            self.audit.record(
                action="auth.mfa_enable",
                organization_id=user.organization_id,
                actor_user_id=user.id,
                resource_type="user",
                resource_id=user.id,
                ip_hash=ip_hash,
            )

    def _issue_tokens(self, *, user: User, ip_hash: str | None) -> TokenResponse:
        permission_keys = sorted(
            self.permissions.get_user_permissions(user_id=user.id, organization_id=user.organization_id)
        )
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            permissions=permission_keys,
        )
        refresh_token = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds),
                ip_hash=ip_hash,
            )
        )
        self.db.flush()
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.access_token_ttl_seconds,
            refresh_token=refresh_token,
        )
