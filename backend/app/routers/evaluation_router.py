from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Optional
from pydantic import BaseModel

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user, require_role
from app.services.audit_log import record_audit_event
from app.tasks.evaluation_tasks import run_full_evaluation_task

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation Engine & Leaderboard"])

class OverrideRequest(BaseModel):
    parameter_scores: Dict[str, float]
    justification_notes: str
    judge_comments: Optional[str] = None

@router.post("/evaluate/{submission_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_full_evaluation(submission_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.status = "evaluating"
    db.commit()

    task = run_full_evaluation_task.delay(submission_id)
    return {"task_id": task.id, "submission_id": submission_id, "status": "queued"}

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
    current_user: models.User = Depends(require_role(["judge", "organizer", "admin"]))
):
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

    record_audit_event(
        db, actor_user_id=current_user.id, action="score_override",
        entity_type="evaluation_report", entity_id=report.id,
        metadata={"parameter_scores": override_data.parameter_scores, "new_final_score": new_final_score},
    )

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
        plag_explanation = report.plagiarism_json.get("explanation") if report and report.plagiarism_json else None
        ai_code_detection = report.static_analysis_json.get("ai_generated_code_detection") if report and report.static_analysis_json else None
        ai_code_risk = ai_code_detection.get("risk_level", "UNKNOWN") if ai_code_detection else "UNKNOWN"
        ai_code_pct = ai_code_detection.get("estimated_ai_usage_percentage") if ai_code_detection else None
        timeline_risk = sub.timeline_risk_json or {}
        timeline_risk_level = timeline_risk.get("risk_level", "LOW")
        timeline_reasoning = timeline_risk.get("reasoning", "")
        repo_verification = report.repo_verification_json if report else None
        repo_red_flags_count = len(repo_verification.get("red_flags", [])) if repo_verification else 0
        repo_claims_checked_count = len(repo_verification.get("claims_checked", [])) if repo_verification else 0
        # Module 12 wants per-parameter scores on the leaderboard itself, not
        # just buried in the individual report - judge overrides take
        # precedence over the raw AI scores, same as final_score does above.
        if report and report.judge_override_json:
            param_scores = report.judge_override_json.get("parameter_scores")
        elif report and report.ai_scores_json:
            param_scores = report.ai_scores_json.get("parameter_scores")
        else:
            param_scores = None

        leaderboard.append({
            "submission_id": sub.id,
            "team_id": sub.team_id,
            "team_name": team.name if team else "Unknown Team",
            "tech_stack": sub.tech_stack or "Not Specified",
            "github_url": sub.github_url,
            "live_url": sub.live_url,
            "score": score,
            "parameter_scores": param_scores,
            "plagiarism_risk": plag_risk,
            "plagiarism_percentage": plag_pct,
            "plagiarism_explanation": plag_explanation,
            "ai_code_risk": ai_code_risk,
            "ai_code_usage_percentage": ai_code_pct,
            "timeline_risk_level": timeline_risk_level,
            "timeline_reasoning": timeline_reasoning,
            "repo_red_flags_count": repo_red_flags_count,
            "repo_claims_checked_count": repo_claims_checked_count,
            "status": sub.status,
            "submitted_at": sub.submitted_at
        })

    # Sort descending by score
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    
    # Assign ranks
    for rank, item in enumerate(leaderboard, start=1):
        item["rank"] = rank

    return leaderboard
