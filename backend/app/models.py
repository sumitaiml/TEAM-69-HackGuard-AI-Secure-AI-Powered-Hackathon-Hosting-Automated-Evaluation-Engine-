import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.dialects.postgresql import ARRAY
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
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True, index=True)
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
    upload_metadata_json = Column(JSON, nullable=True)  # original filenames/sizes/video duration
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

class PlagiarismFingerprint(Base):
    __tablename__ = "plagiarism_fingerprints"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, unique=True)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    # MinHash signature (128 hash values) used for fast candidate shortlisting
    # via a Postgres GIN index on array overlap (&&), avoiding an O(N^2)
    # pairwise comparison across every submission in the hackathon.
    minhash_signature = Column(ARRAY(Integer), nullable=False)
    file_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_plagiarism_fingerprints_minhash_gin", "minhash_signature", postgresql_using="gin"),
    )

class JudgeInvite(Base):
    __tablename__ = "judge_invites"

    id = Column(String, primary_key=True, default=generate_uuid)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    invited_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, accepted, expired, revoked
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # e.g. judge_invite_created, judge_invite_accepted, score_override, rubric_updated
    entity_type = Column(String, nullable=False)  # e.g. judge_invite, evaluation_report, hackathon
    entity_id = Column(String, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
