from celery import Celery

from app.config import settings

celery_app = Celery(
    "hackeval",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # The worker process is started as `celery -A app.celery_app worker`,
    # which only imports this module - without `include`, task modules
    # decorated with @celery_app.task elsewhere are never imported there,
    # so the worker doesn't know they exist ("KeyError: <task name>").
    include=["app.tasks.analysis_tasks", "app.tasks.sandbox_tasks", "app.tasks.evaluation_tasks"],
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
