import os
import shutil
from typing import Optional
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.audit_log import record_audit_event


def cleanup_submission_files(submission_id: str) -> None:
    upload_dir = getattr(settings, "UPLOAD_DIR", "./uploads")
    sub_upload_path = os.path.join(upload_dir, submission_id)
    if os.path.exists(sub_upload_path):
        shutil.rmtree(sub_upload_path, ignore_errors=True)

    workspace_root = getattr(settings, "WORKSPACE_ROOT", "./workspace")
    sub_workspace_path = os.path.join(workspace_root, submission_id)
    if os.path.exists(sub_workspace_path):
        shutil.rmtree(sub_workspace_path, ignore_errors=True)


def delete_submission_cascade(db: Session, submission: models.Submission, actor_user_id: Optional[str] = None) -> None:
    sub_id = submission.id
    hack_id = submission.hackathon_id
    team_id = submission.team_id

    # 1. Delete file-level fingerprints
    db.query(models.PlagiarismFileFingerprint).filter(
        models.PlagiarismFileFingerprint.submission_id == sub_id
    ).delete(synchronize_session=False)

    # 2. Delete submission-level fingerprints
    db.query(models.PlagiarismFingerprint).filter(
        models.PlagiarismFingerprint.submission_id == sub_id
    ).delete(synchronize_session=False)

    # 3. Delete evaluation reports
    db.query(models.EvaluationReport).filter(
        models.EvaluationReport.submission_id == sub_id
    ).delete(synchronize_session=False)

    # 4. Remove physical files on disk
    cleanup_submission_files(sub_id)

    # 5. Audit log
    if actor_user_id:
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="submission_deleted",
            entity_type="submission",
            entity_id=sub_id,
            metadata={"hackathon_id": hack_id, "team_id": team_id},
        )

    # 6. Delete submission row
    db.delete(submission)


def delete_hackathon_cascade(db: Session, hackathon: models.Hackathon, actor_user_id: Optional[str] = None) -> int:
    hack_id = hackathon.id
    hack_title = hackathon.title

    # 1. Delete all submissions and their dependencies
    subs = db.query(models.Submission).filter(models.Submission.hackathon_id == hack_id).all()
    sub_count = len(subs)
    for sub in subs:
        delete_submission_cascade(db, sub, actor_user_id=actor_user_id)

    # 2. Delete judge invites
    db.query(models.JudgeInvite).filter(
        models.JudgeInvite.hackathon_id == hack_id
    ).delete(synchronize_session=False)

    # 3. Delete any remaining plagiarism fingerprints for this hackathon
    db.query(models.PlagiarismFingerprint).filter(
        models.PlagiarismFingerprint.hackathon_id == hack_id
    ).delete(synchronize_session=False)

    # 4. Audit log
    if actor_user_id:
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="hackathon_deleted",
            entity_type="hackathon",
            entity_id=hack_id,
            metadata={"title": hack_title, "submissions_deleted": sub_count},
        )

    # 5. Delete hackathon
    db.delete(hackathon)
    return sub_count

