from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.services.static_analysis import run_static_code_analysis
from app.services.plagiarism_engine import run_plagiarism_check
from app.services.sandbox_runner import execute_in_docker_sandbox

router = APIRouter(prefix="/api/analysis", tags=["Security & Analysis"])

@router.post("/run-static/{submission_id}")
def run_static_analysis_endpoint(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    code_content = sub.readme_text or ""
    report = run_static_code_analysis(code_content=code_content, tech_stack=sub.tech_stack or "")
    return report

@router.post("/plagiarism/{hackathon_id}")
def run_plagiarism_check_endpoint(hackathon_id: str, target_submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    all_subs = db.query(models.Submission).filter(models.Submission.hackathon_id == hackathon_id).all()
    if not all_subs:
        raise HTTPException(status_code=404, detail="No submissions found for this hackathon")

    target_sub = next((s for s in all_subs if s.id == target_submission_id), None)
    if not target_sub:
        raise HTTPException(status_code=404, detail="Target submission not found")

    subs_payload = [
        {"id": s.id, "team_id": s.team_id, "code": s.readme_text or ""}
        for s in all_subs
    ]

    report = run_plagiarism_check(
        target_submission_id=target_submission_id,
        current_code=target_sub.readme_text or "",
        all_submissions=subs_payload
    )
    return report

@router.post("/sandbox/{submission_id}")
def run_sandbox_endpoint(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sandbox_report = execute_in_docker_sandbox(
        submission_id=submission_id,
        github_url=sub.github_url or "",
        zip_path=sub.zip_path or ""
    )
    return sandbox_report
