from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.services.static_analysis import run_static_code_analysis
from app.services.plagiarism_engine import run_plagiarism_check
from app.services.sandbox_runner import execute_in_docker_sandbox
from app.services.ai_evaluation import (
    generate_whisper_transcript,
    analyze_ppt_presentation,
    evaluate_project_with_ai
)

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation Engine & Leaderboard"])

class OverrideRequest(BaseModel):
    parameter_scores: Dict[str, float]
    justification_notes: str
    judge_comments: Optional[str] = None

@router.post("/evaluate/{submission_id}", response_model=schemas.EvaluationReportOut, status_code=status.HTTP_201_CREATED)
def trigger_full_evaluation(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == sub.hackathon_id).first()
    rubric_weights = hackathon.rubric_weights_json if hackathon and hackathon.rubric_weights_json else None

    # 1. Static Analysis
    static_report = run_static_code_analysis(code_content=sub.readme_text or "", tech_stack=sub.tech_stack or "")

    # 2. Plagiarism Check
    all_subs = db.query(models.Submission).filter(models.Submission.hackathon_id == sub.hackathon_id).all()
    subs_payload = [{"id": s.id, "team_id": s.team_id, "code": s.readme_text or ""} for s in all_subs]
    plagiarism_report = run_plagiarism_check(target_submission_id=sub.id, current_code=sub.readme_text or "", all_submissions=subs_payload)

    # 3. Docker Sandbox Execution
    sandbox_report = execute_in_docker_sandbox(submission_id=sub.id, github_url=sub.github_url or "", zip_path=sub.zip_path or "")
    static_report["sandbox_execution"] = sandbox_report

    # 4. Whisper STT & PPT Analysis
    whisper_report = generate_whisper_transcript(video_path=sub.video_path)
    ppt_report = analyze_ppt_presentation(ppt_path=sub.ppt_path)

    # 5. AI Multimodal Evaluation & Weighted Score
    ai_evaluation = evaluate_project_with_ai(
        readme_text=sub.readme_text or "",
        code_content=sub.readme_text or "",
        static_report=static_report,
        plagiarism_report=plagiarism_report,
        whisper_report=whisper_report,
        ppt_report=ppt_report,
        rubric_weights=rubric_weights
    )

    ai_evaluation["whisper_transcript"] = whisper_report
    ai_evaluation["ppt_analysis"] = ppt_report

    new_report = models.EvaluationReport(
        submission_id=sub.id,
        static_analysis_json=static_report,
        plagiarism_json=plagiarism_report,
        ai_scores_json=ai_evaluation,
        final_score=ai_evaluation["overall_score"]
    )

    sub.status = "completed"

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report

@router.get("/report/{submission_id}", response_model=schemas.EvaluationReportOut)
def get_evaluation_report(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    report = db.query(models.EvaluationReport).filter(models.EvaluationReport.submission_id == submission_id).order_by(models.EvaluationReport.created_at.desc()).first()
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation report not found")
    return report

@router.post("/override/{report_id}", response_model=schemas.EvaluationReportOut)
def override_judge_score(
    report_id: str,
    override_data: OverrideRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ["judge", "organizer", "admin"]:
        raise HTTPException(status_code=403, detail="Only judges and organizers can override evaluation scores")

    if not override_data.justification_notes or len(override_data.justification_notes.strip()) < 5:
        raise HTTPException(status_code=400, detail="Mandatory justification notes required for score overrides")

    report = db.query(models.EvaluationReport).filter(models.EvaluationReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation report not found")

    sub = db.query(models.Submission).filter(models.Submission.id == report.submission_id).first()
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == sub.hackathon_id).first() if sub else None
    rubric_weights = hackathon.rubric_weights_json if hackathon and hackathon.rubric_weights_json else {
        "technical_complexity": 30.0, "innovation": 20.0, "ui_ux": 15.0, "business_impact": 15.0, "documentation": 10.0, "presentation": 10.0
    }

    # Recalculate score based on overridden parameters
    new_final_score = sum(
        (override_data.parameter_scores[param] * (weight / 100.0))
        for param, weight in rubric_weights.items()
        if param in override_data.parameter_scores
    )
    new_final_score = round(new_final_score, 2)

    report.judge_override_json = {
        "overridden_by": current_user.full_name,
        "overridden_by_id": current_user.id,
        "parameter_scores": override_data.parameter_scores,
        "justification": override_data.justification_notes
    }
    report.judge_comments = override_data.judge_comments
    report.final_score = new_final_score

    db.commit()
    db.refresh(report)

    return report

@router.get("/leaderboard/{hackathon_id}")
def get_hackathon_leaderboard(hackathon_id: str, db: Session = Depends(get_db)):
    submissions = db.query(models.Submission).filter(models.Submission.hackathon_id == hackathon_id).all()
    
    leaderboard = []
    for sub in submissions:
        report = db.query(models.EvaluationReport).filter(models.EvaluationReport.submission_id == sub.id).order_by(models.EvaluationReport.created_at.desc()).first()
        team = db.query(models.Team).filter(models.Team.id == sub.team_id).first()
        
        score = report.final_score if report else 0.0
        plag_risk = report.plagiarism_json.get("risk_level", "LOW") if report and report.plagiarism_json else "LOW"
        plag_pct = report.plagiarism_json.get("similarity_percentage", 0.0) if report and report.plagiarism_json else 0.0

        leaderboard.append({
            "submission_id": sub.id,
            "team_id": sub.team_id,
            "team_name": team.name if team else "Unknown Team",
            "tech_stack": sub.tech_stack or "Not Specified",
            "github_url": sub.github_url,
            "live_url": sub.live_url,
            "score": score,
            "plagiarism_risk": plag_risk,
            "plagiarism_percentage": plag_pct,
            "status": sub.status,
            "submitted_at": sub.submitted_at
        })

    # Sort descending by score
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    
    # Assign ranks
    for rank, item in enumerate(leaderboard, start=1):
        item["rank"] = rank

    return leaderboard
