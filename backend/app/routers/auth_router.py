import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.audit_log import record_audit_event
from app.services.email_service import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = get_password_hash(user_in.password)
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role,
        verification_token=secrets.token_urlsafe(32),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Verification is informational, not a login gate - a hackathon-scale MVP
    # shouldn't add friction to registration, so is_verified has no effect on
    # auth today. Sent fire-and-forget; a delivery failure here must not
    # block account creation itself.
    verify_link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={new_user.verification_token}"
    send_verification_email(new_user.email, verify_link)

    token = create_access_token(data={"sub": new_user.id, "role": new_user.role})
    return {"access_token": token, "token_type": "bearer", "user": new_user}


@router.get("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or already-used verification link")

    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully."}


@router.post("/forgot-password")
def forgot_password(body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always returns the same response regardless of whether the email is
    # registered - a different response would let an attacker enumerate
    # which emails have accounts.
    generic_response = {"message": "If an account with that email exists, a password reset link has been sent."}

    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user:
        return generic_response

    token = secrets.token_urlsafe(32)
    db.add(models.PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_EXPIRY_HOURS),
    ))
    db.commit()

    reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
    dev_reset_link = send_password_reset_email(user.email, reset_link)
    if dev_reset_link:
        generic_response["dev_reset_link"] = dev_reset_link
    return generic_response


@router.post("/reset-password/{token}")
def reset_password(token: str, body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token == token).first()
    if not reset:
        raise HTTPException(status_code=404, detail="Invalid or expired reset link")
    if reset.used_at is not None:
        raise HTTPException(status_code=400, detail="This reset link has already been used")
    if reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset link has expired")

    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account no longer exists")

    user.hashed_password = get_password_hash(body.new_password)
    reset.used_at = datetime.utcnow()
    db.commit()
    return {"message": "Password has been reset successfully."}

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


def _get_pending_invite_or_404(token: str, db: Session) -> models.JudgeInvite:
    invite = db.query(models.JudgeInvite).filter(models.JudgeInvite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail=f"This invite has already been {invite.status}")
    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="This invite has expired")
    return invite


@router.get("/invite/{token}", response_model=schemas.InviteDetailsOut)
def get_invite_details(token: str, db: Session = Depends(get_db)):
    invite = _get_pending_invite_or_404(token, db)
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == invite.hackathon_id).first()
    return schemas.InviteDetailsOut(
        email=invite.email,
        hackathon_id=invite.hackathon_id,
        hackathon_title=hackathon.title if hackathon else "Unknown Hackathon",
        status=invite.status,
        expires_at=invite.expires_at,
    )


@router.post("/invite/{token}/accept", response_model=schemas.Token)
def accept_judge_invite(token: str, accept_in: schemas.InviteAcceptRequest, db: Session = Depends(get_db)):
    invite = _get_pending_invite_or_404(token, db)

    existing = db.query(models.User).filter(models.User.email == invite.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    new_user = models.User(
        email=invite.email,
        hashed_password=get_password_hash(accept_in.password),
        full_name=accept_in.full_name,
        role="judge",
    )
    db.add(new_user)
    db.flush()  # assigns new_user.id for use below, without committing yet

    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()

    record_audit_event(
        db, actor_user_id=new_user.id, action="judge_invite_accepted",
        entity_type="judge_invite", entity_id=invite.id,
        metadata={"hackathon_id": invite.hackathon_id, "email": invite.email},
    )

    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.id, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer", "user": new_user}
