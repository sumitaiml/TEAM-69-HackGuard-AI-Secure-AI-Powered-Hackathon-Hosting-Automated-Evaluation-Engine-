import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.auth import require_role
from app.services.audit_log import record_audit_event
from app.services.email_service import send_judge_invite_email

router = APIRouter(prefix="/api/hackathons", tags=["Hackathons"])

@router.get("", response_model=List[schemas.HackathonOut])
def list_hackathons(db: Session = Depends(get_db)):
    return db.query(models.Hackathon).filter(models.Hackathon.is_active == True).all()

@router.post("/create", response_model=schemas.HackathonOut, status_code=status.HTTP_201_CREATED)
def create_hackathon(hack_in: schemas.HackathonCreate, current_user: models.User = Depends(require_role(["organizer", "admin"])), db: Session = Depends(get_db)):
    rubric_dict = hack_in.rubric_weights.model_dump() if hack_in.rubric_weights else {
        "technical_complexity": 30.0,
        "innovation": 20.0,
        "ui_ux": 15.0,
        "business_impact": 15.0,
        "documentation": 10.0,
        "presentation": 10.0
    }

    new_hack = models.Hackathon(
        title=hack_in.title,
        description=hack_in.description,
        start_date=hack_in.start_date or datetime.utcnow(),
        end_date=hack_in.end_date,
        rubric_weights_json=rubric_dict
    )
    db.add(new_hack)
    db.commit()
    db.refresh(new_hack)

    return new_hack

@router.put("/{hackathon_id}/rubric", response_model=schemas.HackathonOut)
def update_rubric(hackathon_id: str, rubric_in: schemas.RubricConfig, current_user: models.User = Depends(require_role(["organizer", "admin"])), db: Session = Depends(get_db)):
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    rubric_dict = rubric_in.model_dump()
    total_sum = sum(rubric_dict.values())
    if abs(total_sum - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Rubric weights must sum to 100%. Current sum: {total_sum}%")

    hackathon.rubric_weights_json = rubric_dict

    record_audit_event(
        db, actor_user_id=current_user.id, action="rubric_updated",
        entity_type="hackathon", entity_id=hackathon.id,
        metadata={"new_weights": rubric_dict},
    )

    db.commit()
    db.refresh(hackathon)

    return hackathon


@router.post("/{hackathon_id}/invite-judge", status_code=status.HTTP_201_CREATED)
def invite_judge(
    hackathon_id: str,
    invite_in: schemas.JudgeInviteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["organizer", "admin"])),
):
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    existing_user = db.query(models.User).filter(models.User.email == invite_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email already has an account")

    token = secrets.token_urlsafe(32)
    invite = models.JudgeInvite(
        hackathon_id=hackathon_id,
        email=invite_in.email,
        token=token,
        invited_by_user_id=current_user.id,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=settings.JUDGE_INVITE_EXPIRY_DAYS),
    )
    db.add(invite)
    db.flush()  # assigns invite.id for the audit log entry below

    record_audit_event(
        db, actor_user_id=current_user.id, action="judge_invite_created",
        entity_type="judge_invite", entity_id=invite.id,
        metadata={"hackathon_id": hackathon_id, "email": invite_in.email},
    )

    db.commit()
    db.refresh(invite)

    invite_link = f"{settings.FRONTEND_BASE_URL}/accept-invite?token={token}"
    dev_invite_link = send_judge_invite_email(invite_in.email, invite_link, hackathon.title)

    response = schemas.JudgeInviteOut.model_validate(invite).model_dump()
    if dev_invite_link:
        response["dev_invite_link"] = dev_invite_link
    return response
