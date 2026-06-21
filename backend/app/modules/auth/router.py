from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_principal
from app.core.security import hash_ip
from app.core.tenant import Principal
from app.modules.auth.service import (
    AuthService,
    LoginRequest,
    MfaConfirmRequest,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterOrganizationRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/register-organization", response_model=TokenResponse)
def register_organization(
    payload: RegisterOrganizationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    service = AuthService(db)
    _, _, tokens = service.register_organization(payload, ip_hash=_hash_ip(request))
    db.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    tokens = service.login(payload, ip_hash=_hash_ip(request))
    db.commit()
    return tokens


@router.post("/mfa/verify", response_model=TokenResponse)
def verify_mfa(payload: MfaVerifyRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    tokens = service.verify_mfa(payload, ip_hash=_hash_ip(request))
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    tokens = service.refresh(payload, ip_hash=_hash_ip(request))
    db.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    service = AuthService(db)
    service.logout(payload, user_id=principal.user_id, ip_hash=_hash_ip(request))
    db.commit()


@router.get("/me", response_model=UserResponse)
def me(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> UserResponse:
    service = AuthService(db)
    return service.get_me(principal.user_id, principal.organization_id)


@router.post("/mfa/enroll")
def enroll_mfa(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    service = AuthService(db)
    result = service.enroll_mfa(principal.user_id)
    db.commit()
    return result


@router.post("/mfa/confirm", status_code=204)
def confirm_mfa(
    payload: MfaConfirmRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    service = AuthService(db)
    service.confirm_mfa(principal.user_id, payload.code, ip_hash=_hash_ip(request))
    db.commit()


def _hash_ip(request: Request) -> str | None:
    ip = _client_ip(request)
    return hash_ip(ip) if ip else None
