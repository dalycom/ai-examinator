import hashlib
import json
import uuid
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db, tenant_session
from app.core.enums import Locale
from app.core.errors import AppError
from app.core.models import User
from app.core.security import decode_token
from app.core.tenant import Principal
from app.modules.rbac.service import PermissionService

settings = get_settings()


def get_request_locale(
    accept_language: str | None = Header(default=None),
) -> Locale:
    if not accept_language:
        return settings.default_locale
    for part in accept_language.split(","):
        code = part.strip().split(";")[0].lower()
        for locale in settings.supported_locale_list:
            if locale.value == code:
                return locale
    return settings.default_locale


def get_trace_id(request: Request) -> str:
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    return trace_id


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
    locale: Locale = Depends(get_request_locale),
    authorization: str | None = Header(default=None),
) -> Principal:
    request.state.locale = locale.value
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            code="UNAUTHORIZED",
            message_key="errors.unauthorized",
            status_code=401,
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise AppError(
            code="UNAUTHORIZED",
            message_key="errors.unauthorized",
            status_code=401,
        ) from exc

    if payload.get("type") != "access":
        raise AppError(
            code="UNAUTHORIZED",
            message_key="errors.unauthorized",
            status_code=401,
        )

    user_id = UUID(payload["sub"])
    organization_id = UUID(payload["org"])
    permissions = frozenset(payload.get("permissions", []))

    with tenant_session(db, organization_id):
        user = db.get(User, user_id)
        if user is None or user.status != "active" or user.organization_id != organization_id:
            raise AppError(
                code="UNAUTHORIZED",
                message_key="errors.unauthorized",
                status_code=401,
            )

    return Principal(
        user_id=user_id,
        organization_id=organization_id,
        permissions=permissions,
        locale=Locale(user.preferred_locale),
        email=user.email,
        full_name=user.full_name,
    )


def require_permission(permission: str) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if permission not in principal.permissions:
            raise AppError(
                code="FORBIDDEN",
                message_key="errors.forbidden",
                status_code=403,
            )
        return principal

    return dependency


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    return PermissionService(db)


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_record_hash(prev_hash: str | None, payload: dict[str, Any]) -> str:
    material = f"{prev_hash or ''}|{canonical_json(payload)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
