from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = "participant" # participant, organizer, judge

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    full_name: str
    role: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Team Schemas ---
class TeamCreate(BaseModel):
    name: str

class TeamJoin(BaseModel):
    invite_code: str

class TeamMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user: UserOut
    joined_at: datetime

class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    invite_code: str
    leader_id: str
    created_at: datetime
    members: List[TeamMemberOut] = []

# --- Hackathon & Rubric Schemas ---
class RubricConfig(BaseModel):
    technical_complexity: float = 30.0
    innovation: float = 20.0
    ui_ux: float = 15.0
    business_impact: float = 15.0
    documentation: float = 10.0
    presentation: float = 10.0

class HackathonCreate(BaseModel):
    title: str
    description: Optional[str] = None
    rubric_weights: Optional[RubricConfig] = Field(default_factory=RubricConfig)

class HackathonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: str
    description: Optional[str]
    rubric_weights_json: Optional[Dict[str, float]]
    is_active: bool
    created_at: datetime

# --- Submission Schemas ---
class SubmissionCreate(BaseModel):
    hackathon_id: str
    github_url: Optional[str] = None
    readme_text: Optional[str] = None
    tech_stack: Optional[str] = None
    live_url: Optional[str] = None

class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    team_id: str
    hackathon_id: str
    github_url: Optional[str]
    zip_path: Optional[str]
    ppt_path: Optional[str]
    video_path: Optional[str]
    readme_text: Optional[str]
    tech_stack: Optional[str]
    live_url: Optional[str]
    status: str
    upload_metadata_json: Optional[Dict[str, Any]] = None
    submitted_at: datetime

# --- Evaluation Schemas ---
class EvaluationReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    submission_id: str
    static_analysis_json: Optional[Dict[str, Any]]
    plagiarism_json: Optional[Dict[str, Any]]
    ai_scores_json: Optional[Dict[str, Any]]
    final_score: float
    judge_override_json: Optional[Dict[str, Any]]
    judge_comments: Optional[str]
    created_at: datetime
