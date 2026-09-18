from celery import Celery

from app.config import settings

celery_app = Celery(
    "hackguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
)


@celery_app.task(name="health_check")
def health_check_task():
    return {"status": "ok"}
