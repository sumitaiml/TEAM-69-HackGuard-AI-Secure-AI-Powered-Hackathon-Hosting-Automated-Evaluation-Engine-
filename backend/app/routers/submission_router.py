import os
import shutil
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    membership = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of the specified team")

    # Check hackathon exists
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    sub_id = str(uuid.uuid4())
    team_upload_dir = os.path.join(UPLOAD_DIR, sub_id)
    os.makedirs(team_upload_dir, exist_ok=True)

    zip_path_saved = None
    if zip_file:
        zip_path_saved = os.path.join(team_upload_dir, zip_file.filename)
        with open(zip_path_saved, "wb") as buffer:
            shutil.copyfileobj(zip_file.file, buffer)

    ppt_path_saved = None
    if ppt_file:
        ppt_path_saved = os.path.join(team_upload_dir, ppt_file.filename)
        with open(ppt_path_saved, "wb") as buffer:
            shutil.copyfileobj(ppt_file.file, buffer)

    video_path_saved = None
    if video_file:
        video_path_saved = os.path.join(team_upload_dir, video_file.filename)
        with open(video_path_saved, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)

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
        status="submitted"
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
    return sub

@router.get("/team/{team_id}", response_model=List[schemas.SubmissionOut])
def get_team_submissions(team_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    subs = db.query(models.Submission).filter(models.Submission.team_id == team_id).all()
    return subs
