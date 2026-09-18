from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db
from app.auth import require_role

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
    db.commit()
    db.refresh(hackathon)

    return hackathon
