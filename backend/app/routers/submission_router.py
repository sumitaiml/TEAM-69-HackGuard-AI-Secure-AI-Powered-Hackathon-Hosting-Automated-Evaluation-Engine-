import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.services.upload_validation import (
    ALLOWED_ZIP_EXTENSIONS,
    ALLOWED_PPT_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    validate_extension,
    save_upload_streamed,
    validate_zip_structure,
    validate_video_duration,
)
from app.config import settings

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _is_team_member(db: Session, team_id: str, user_id: str) -> bool:
    return db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == user_id
    ).first() is not None


@router.post("/upload", response_model=schemas.SubmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_project(
    hackathon_id: str = Form(...),
    team_id: str = Form(...),
    github_url: Optional[str] = Form(None),
    readme_text: Optional[str] = Form(None),
    tech_stack: Optional[str] = Form(None),
    live_url: Optional[str] = Form(None),
    zip_file: Optional[UploadFile] = File(None),
    ppt_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check team membership
    if not _is_team_member(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="User is not a member of the specified team")

    # Check hackathon exists
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    sub_id = str(uuid.uuid4())
    team_upload_dir = os.path.join(UPLOAD_DIR, sub_id)
    os.makedirs(team_upload_dir, exist_ok=True)

    upload_metadata = {}

    # Files are always written under a fixed, server-chosen name inside the
    # submission's own uuid directory - the client-supplied filename is never
    # used as a path component, so path traversal is impossible by construction.
    # The original filename is preserved only as display metadata below.
    zip_path_saved = None
    if zip_file:
        validate_extension(zip_file.filename, ALLOWED_ZIP_EXTENSIONS, "zip_file")
        zip_path_saved = os.path.join(team_upload_dir, "source.zip")
        size = save_upload_streamed(zip_file, zip_path_saved, settings.MAX_ZIP_SIZE_MB, "zip_file")
        validate_zip_structure(zip_path_saved, "zip_file")
        upload_metadata["zip"] = {"original_filename": zip_file.filename, "size_bytes": size}

    ppt_path_saved = None
    if ppt_file:
        validate_extension(ppt_file.filename, ALLOWED_PPT_EXTENSIONS, "ppt_file")
        ppt_path_saved = os.path.join(team_upload_dir, "deck.pptx")
        size = save_upload_streamed(ppt_file, ppt_path_saved, settings.MAX_PPT_SIZE_MB, "ppt_file")
        validate_zip_structure(ppt_path_saved, "ppt_file")
        upload_metadata["ppt"] = {"original_filename": ppt_file.filename, "size_bytes": size}

    video_path_saved = None
    if video_file:
        ext = validate_extension(video_file.filename, ALLOWED_VIDEO_EXTENSIONS, "video_file")
        video_path_saved = os.path.join(team_upload_dir, f"demo{ext}")
        size = save_upload_streamed(video_file, video_path_saved, settings.MAX_VIDEO_SIZE_MB, "video_file")
        duration = validate_video_duration(video_path_saved, "video_file")
        upload_metadata["video"] = {
            "original_filename": video_file.filename,
            "size_bytes": size,
            "duration_seconds": duration,
        }

    new_submission = models.Submission(
        id=sub_id,
        team_id=team_id,
        hackathon_id=hackathon_id,
        github_url=github_url,
        zip_path=zip_path_saved,
        ppt_path=ppt_path_saved,
        video_path=video_path_saved,
        readme_text=readme_text,
        tech_stack=tech_stack,
        live_url=live_url,
        status="submitted",
        upload_metadata_json=upload_metadata or None,
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    return new_submission


@router.get("/{submission_id}", response_model=schemas.SubmissionOut)
def get_submission(submission_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # TODO(Phase 8): once JudgeInvite exists, scope judge/organizer access to
    # only the hackathons they're actually attached to, not every hackathon.
    if current_user.role not in ("organizer", "judge", "admin") and not _is_team_member(db, sub.team_id, current_user.id):
        raise HTTPException(status_code=403, detail="You do not have access to this submission")

    return sub


@router.get("/team/{team_id}", response_model=List[schemas.SubmissionOut])
def get_team_submissions(team_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # TODO(Phase 8): scope judge/organizer access to their own hackathons only.
    if current_user.role not in ("organizer", "judge", "admin") and not _is_team_member(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="You do not have access to this team's submissions")

    subs = db.query(models.Submission).filter(models.Submission.team_id == team_id).all()
    return subs
