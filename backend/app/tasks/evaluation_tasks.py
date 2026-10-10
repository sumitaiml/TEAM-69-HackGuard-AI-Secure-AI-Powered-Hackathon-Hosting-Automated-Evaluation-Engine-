import logging

from app.celery_app import celery_app
from app import database, models
from app.config import settings
from app.services.source_fetch import extract_submission_source
from app.services.static_analysis import run_static_code_analysis
from app.services.plagiarism_engine import run_plagiarism_check
from app.services.plagiarism_explainer_agent import run_plagiarism_explainer_agent
from app.services.ai_code_detection import run_ai_code_detection_check
from app.services.timeline_agent import run_timeline_risk_check
from app.services.repo_verification_agent import run_repo_verification_agent
from app.services.sandbox_runner import execute_in_docker_sandbox
from app.services.whisper_engine import generate_whisper_transcript
from app.services.ppt_engine import analyze_ppt_presentation
from app.services.ai_evaluation import evaluate_project_with_ai

logger = logging.getLogger(__name__)


@celery_app.task(name="run_full_evaluation_task", bind=True)
def run_full_evaluation_task(self, submission_id: str):
    """The single evaluation pipeline task, run entirely on the worker (the
    only process with Docker socket access) - calls the real service
    functions directly in sequence rather than chaining separate Celery
    tasks, since the slowest step (sandbox execution, up to 60s) dominates
    the pipeline anyway and a plain sequence avoids Celery chain/chord
    argument-passing complexity for no real parallelism gain."""
    db = database.SessionLocal()
    try:
        sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
        if not sub:
            return {"error": "Submission not found"}

        hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == sub.hackathon_id).first()
        rubric_weights = hackathon.rubric_weights_json if hackathon and hackathon.rubric_weights_json else None

        try:
            self.update_state(state="PROGRESS", meta={"stage": "extracting_source"})
            source_dir = extract_submission_source(sub)

            self.update_state(state="PROGRESS", meta={"stage": "static_analysis"})
            static_report = run_static_code_analysis(source_dir)
            static_report["ai_generated_code_detection"] = run_ai_code_detection_check(source_dir)

            self.update_state(state="PROGRESS", meta={"stage": "repo_verification"})
            repo_verification_report = run_repo_verification_agent(source_dir, sub.readme_text or "")

            self.update_state(state="PROGRESS", meta={"stage": "plagiarism_check"})
            plagiarism_report = run_plagiarism_check(db, sub, source_dir)
            if (
                settings.ENABLE_PLAGIARISM_EXPLAINER_AGENT
                and plagiarism_report.get("risk_level") in ("MEDIUM", "CRITICAL")
                and plagiarism_report.get("flagged_matching_submission_id")
            ):
                plagiarism_report["explanation"] = run_plagiarism_explainer_agent(
                    db, sub.id, plagiarism_report["flagged_matching_submission_id"], source_dir,
                )

            self.update_state(state="PROGRESS", meta={"stage": "timeline_check"})
            sub.timeline_risk_json = run_timeline_risk_check(sub, hackathon.start_date if hackathon else None)

            self.update_state(state="PROGRESS", meta={"stage": "sandbox_execution"})
            sandbox_report = execute_in_docker_sandbox(submission_id=sub.id, source_dir=source_dir)
            static_report["sandbox_execution"] = sandbox_report

            self.update_state(state="PROGRESS", meta={"stage": "media_analysis"})
            whisper_report = generate_whisper_transcript(sub.video_path)
            ppt_report = analyze_ppt_presentation(sub.ppt_path, sub.id)

            self.update_state(state="PROGRESS", meta={"stage": "ai_scoring"})
            ai_evaluation = evaluate_project_with_ai(
                readme_text=sub.readme_text or "",
                tech_stack=sub.tech_stack or "",
                static_report=static_report,
                plagiarism_report=plagiarism_report,
                whisper_report=whisper_report,
                ppt_report=ppt_report,
                rubric_weights=rubric_weights,
            )
            ai_evaluation["whisper_transcript"] = whisper_report
            ai_evaluation["ppt_analysis"] = ppt_report

            report = models.EvaluationReport(
                submission_id=sub.id,
                static_analysis_json=static_report,
                plagiarism_json=plagiarism_report,
                ai_scores_json=ai_evaluation,
                repo_verification_json=repo_verification_report,
                final_score=ai_evaluation["overall_score"],
            )
            sub.status = "completed"
            db.add(report)
            db.commit()
            db.refresh(report)

            return {
                "report_id": report.id,
                "submission_id": sub.id,
                "final_score": report.final_score,
                "ai_evaluation_degraded": ai_evaluation.get("ai_evaluation_degraded", False),
            }
        except Exception:
            sub.status = "failed"
            db.commit()
            logger.exception("Evaluation pipeline failed for submission %s", submission_id)
            raise
    finally:
        db.close()
