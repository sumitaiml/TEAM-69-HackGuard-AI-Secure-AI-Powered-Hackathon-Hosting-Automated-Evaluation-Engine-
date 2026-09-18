from fastapi import APIRouter, Depends
from celery.result import AsyncResult

from app import models
from app.auth import get_current_user
from app.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("/{task_id}")
def get_task_status(task_id: str, current_user: models.User = Depends(get_current_user)):
    """Generic polling endpoint reused by every async (Celery-backed) feature -
    static analysis, plagiarism, sandbox execution, and the full evaluation
    pipeline all return a task_id here instead of a bespoke status endpoint each."""
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "status": result.status}
    if result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)
    return response
