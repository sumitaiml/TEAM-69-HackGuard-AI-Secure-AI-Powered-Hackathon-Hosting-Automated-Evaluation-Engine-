from app.celery_app import celery_app
from app import database
from app import models
from app.services.source_fetch import extract_submission_source
from app.services.static_analysis import run_static_code_analysis
from app.services.plagiarism_engine import run_plagiarism_check
from app.services.sandbox_runner import execute_in_docker_sandbox


@celery_app.task(name="run_static_analysis_task")
def run_static_analysis_task(submission_id: str):
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            return {"error": "Submission not found"}
        source_dir = extract_submission_source(sub)
        return run_static_code_analysis(source_dir)
    finally:
        db.close()


@celery_app.task(name="run_plagiarism_task")
def run_plagiarism_task(submission_id: str):
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            return {"error": "Submission not found"}
        source_dir = extract_submission_source(sub)
        return run_plagiarism_check(db, sub, source_dir)
    finally:
        db.close()


@celery_app.task(name="run_sandbox_task")
def run_sandbox_task(submission_id: str):
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            return {"error": "Submission not found"}
        return execute_in_docker_sandbox(
            submission_id=sub.id, github_url=sub.github_url or "", zip_path=sub.zip_path or ""
        )
    finally:
        db.close()
