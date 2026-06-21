from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def tenant_session(db: Session, organization_id: UUID | None) -> Generator[Session, None, None]:
    """Set Postgres RLS tenant context for the current transaction."""
    if organization_id is not None:
        db.execute(
            text("SELECT set_config('app.current_organization_id', :org_id, true)"),
            {"org_id": str(organization_id)},
        )
    try:
        yield db
    finally:
        db.execute(text("SELECT set_config('app.current_organization_id', '', true)"))


@contextmanager
def bypass_tenant_rls_session(db: Session) -> Generator[Session, None, None]:
    """Clear tenant RLS filter for cross-tenant auth lookups (e.g. login by email)."""
    db.execute(text("SELECT set_config('app.current_organization_id', '', true)"))
    try:
        yield db
    finally:
        db.execute(text("SELECT set_config('app.current_organization_id', '', true)"))


@event.listens_for(engine, "connect")
def _register_citext(dbapi_connection: Any, _connection_record: Any) -> None:
    # citext is created in migrations; ignore if unavailable in lightweight test DBs
    pass
