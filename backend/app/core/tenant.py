from dataclasses import dataclass
from uuid import UUID

from app.core.enums import Locale


@dataclass(frozen=True)
class TenantContext:
    organization_id: UUID
    user_id: UUID
    permissions: frozenset[str]
    locale: Locale


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    organization_id: UUID
    permissions: frozenset[str]
    locale: Locale
    email: str
    full_name: str
