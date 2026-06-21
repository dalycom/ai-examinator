from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("ai_examinator", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_default_queue = "default"
celery_app.autodiscover_tasks(["app.workers.tasks"])


@celery_app.task(name="health.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"
