import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="participant")  # participant, organizer, judge
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teams_led = relationship("Team", back_populates="leader")
    team_memberships = relationship("TeamMember", back_populates="user")

class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    invite_code = Column(String, unique=True, index=True, nullable=False)
    leader_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    leader = relationship("User", back_populates="teams_led")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    rubric_weights_json = Column(JSON, nullable=True) # e.g. {"technical": 30, "innovation": 20, ...}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submissions = relationship("Submission", back_populates="hackathon")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    github_url = Column(String, nullable=True)
    zip_path = Column(String, nullable=True)
    ppt_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    readme_text = Column(Text, nullable=True)
    tech_stack = Column(String, nullable=True)
    live_url = Column(String, nullable=True)
    status = Column(String, default="submitted") # submitted, evaluating, completed, failed
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    team = relationship("Team", back_populates="submissions")
    hackathon = relationship("Hackathon", back_populates="submissions")
    reports = relationship("EvaluationReport", back_populates="submission", cascade="all, delete-orphan")

class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    static_analysis_json = Column(JSON, nullable=True)
    plagiarism_json = Column(JSON, nullable=True)
    ai_scores_json = Column(JSON, nullable=True)
    final_score = Column(Float, default=0.0)
    judge_override_json = Column(JSON, nullable=True)
    judge_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submission = relationship("Submission", back_populates="reports")
