import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/teams", tags=["Teams"])

def generate_short_code():
    return uuid.uuid4().hex[:6].upper()

@router.post("/create", response_model=schemas.TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(team_in: schemas.TeamCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = generate_short_code()
    new_team = models.Team(
        name=team_in.name,
        invite_code=code,
        leader_id=current_user.id
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    # Add leader as member
    leader_member = models.TeamMember(team_id=new_team.id, user_id=current_user.id)
    db.add(leader_member)
    db.commit()
    db.refresh(new_team)

    return new_team

@router.post("/join", response_model=schemas.TeamOut)
def join_team(join_in: schemas.TeamJoin, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.invite_code == join_in.invite_code.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Invalid team invite code")

    existing_membership = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team.id,
        models.TeamMember.user_id == current_user.id
    ).first()

    if existing_membership:
        return team

    new_member = models.TeamMember(team_id=team.id, user_id=current_user.id)
    db.add(new_member)
    db.commit()
    db.refresh(team)

    return team

@router.get("/my-team", response_model=List[schemas.TeamOut])
def get_my_teams(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(models.TeamMember).filter(models.TeamMember.user_id == current_user.id).all()
    team_ids = [m.team_id for m in memberships]
    teams = db.query(models.Team).filter(models.Team.id.in_(team_ids)).all() if team_ids else []
    return teams
