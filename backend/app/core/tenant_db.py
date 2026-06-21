from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db, tenant_session
from app.core.dependencies import get_current_principal
from app.core.tenant import Principal


def get_tenant_db(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Generator[Session, None, None]:
    with tenant_session(db, principal.organization_id):
        yield db
