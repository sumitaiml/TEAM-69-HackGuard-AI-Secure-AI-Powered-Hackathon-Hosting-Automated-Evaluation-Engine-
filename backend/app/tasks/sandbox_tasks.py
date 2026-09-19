from app.celery_app import celery_app
from app import database
from app import models
from app.services.source_fetch import extract_submission_source
from app.services.sandbox_runner import execute_in_docker_sandbox


@celery_app.task(name="run_sandbox_task")
def run_sandbox_task(submission_id: str):
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            return {"error": "Submission not found"}
        source_dir = extract_submission_source(sub)
        return execute_in_docker_sandbox(submission_id=sub.id, source_dir=source_dir)
    finally:
        db.close()
