from app.celery_app import health_check_task


def test_celery_task_runs_synchronously_in_eager_mode():
    result = health_check_task.delay()
    assert result.get(timeout=5) == {"status": "ok"}
