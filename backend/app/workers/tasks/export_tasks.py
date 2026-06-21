from uuid import UUID

from app.core.database import SessionLocal
from app.core.enums import Locale
from app.core.tenant import Principal
from app.workers.celery_app import celery_app


def _worker_principal(*, organization_id: UUID, user_id: UUID) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=organization_id,
        permissions=frozenset({"export:run", "erasure:run", "patient:read", "governance:manage"}),
        locale=Locale.EN,
        email="worker@internal.local",
        full_name="Background Worker",
    )


@celery_app.task(name="export.run_job")  # type: ignore[untyped-decorator]
def run_export_job(job_id: str, organization_id: str, user_id: str) -> str:
    from app.modules.integrations.service import IntegrationsService

    db = SessionLocal()
    try:
        principal = _worker_principal(
            organization_id=UUID(organization_id),
            user_id=UUID(user_id),
        )
        service = IntegrationsService(db)
        service.execute_export_job(UUID(job_id), principal)
        db.commit()
        return job_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
