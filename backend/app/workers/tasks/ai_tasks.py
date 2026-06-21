from uuid import UUID

from app.core.database import SessionLocal
from app.core.enums import Locale
from app.core.tenant import Principal
from app.workers.celery_app import celery_app


def _worker_principal(*, organization_id: UUID, user_id: UUID) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=organization_id,
        permissions=frozenset({"ai:run", "ai:read", "ai:review", "governance:manage"}),
        locale=Locale.EN,
        email="worker@internal.local",
        full_name="Background Worker",
    )


@celery_app.task(name="ai.run_extraction")  # type: ignore[untyped-decorator]
def run_ai_extraction(run_id: str, organization_id: str, user_id: str) -> str:
    from app.modules.ai.service import AIService

    db = SessionLocal()
    try:
        principal = _worker_principal(
            organization_id=UUID(organization_id),
            user_id=UUID(user_id),
        )
        service = AIService(db)
        service.execute_extraction_run(UUID(run_id), principal)
        db.commit()
        return run_id
    except Exception as exc:
        db.rollback()
        db2 = SessionLocal()
        try:
            AIService(db2).mark_extraction_failed(UUID(run_id), UUID(organization_id), str(exc))
            db2.commit()
        finally:
            db2.close()
        raise
    finally:
        db.close()
