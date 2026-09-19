from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.auth import get_current_user
from app.tasks.analysis_tasks import run_static_analysis_task, run_plagiarism_task
from app.tasks.sandbox_tasks import run_sandbox_task

router = APIRouter(prefix="/api/analysis", tags=["Security & Analysis"])


def _get_submission_or_404(submission_id: str, db: Session) -> models.Submission:
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.post("/run-static/{submission_id}", status_code=status.HTTP_202_ACCEPTED)
def run_static_analysis_endpoint(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _get_submission_or_404(submission_id, db)
    task = run_static_analysis_task.delay(submission_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/plagiarism/{submission_id}", status_code=status.HTTP_202_ACCEPTED)
def run_plagiarism_check_endpoint(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _get_submission_or_404(submission_id, db)
    task = run_plagiarism_task.delay(submission_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/sandbox/{submission_id}", status_code=status.HTTP_202_ACCEPTED)
def run_sandbox_endpoint(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _get_submission_or_404(submission_id, db)
    task = run_sandbox_task.delay(submission_id)
    return {"task_id": task.id, "status": "queued"}
