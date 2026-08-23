"""
CloudPrep AI — SQLAlchemy models.
All CloudPrep platform data lives here.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Boolean, ForeignKey
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Learning Topic + Sub-topics
# ---------------------------------------------------------------------------

class LearningTopic(Base):
    """
    A top-level cloud engineering topic (e.g. Linux, AWS, Docker).
    progress_pct is 0–100 maintained by the app.
    sub_topics is a JSON list of { name, progress_pct, order }.
    """
    __tablename__ = "cloudprep_topics"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    icon = Column(String(10), default="📘")
    color = Column(String(30), default="#6366f1")
    order = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    # [{ name, progress_pct, order, completed }]
    sub_topics = Column(JSON, nullable=False, default=list)
    # total minutes studied for this topic
    total_study_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Study Session (daily log)
# ---------------------------------------------------------------------------

class StudySession(Base):
    """
    One study session block — topic, duration, notes.
    """
    __tablename__ = "cloudprep_sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    topic_id = Column(String(36), ForeignKey("cloudprep_topics.id", ondelete="SET NULL"), nullable=True)
    topic_name = Column(String(120), nullable=True)   # denorm for easy read
    duration_minutes = Column(Integer, default=30)
    xp_earned = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    session_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Daily Goal
# ---------------------------------------------------------------------------

class DailyGoal(Base):
    """
    Per-day XP goal and completion tracking.
    """
    __tablename__ = "cloudprep_daily_goals"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    goal_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    target_minutes = Column(Integer, default=60)
    actual_minutes = Column(Integer, default=0)
    target_xp = Column(Integer, default=100)
    actual_xp = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

class Note(Base):
    """
    User notes per topic, supports markdown.
    """
    __tablename__ = "cloudprep_notes"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    topic_id = Column(String(36), ForeignKey("cloudprep_topics.id", ondelete="SET NULL"), nullable=True)
    topic_name = Column(String(120), nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")   # markdown
    tags = Column(JSON, default=list)    # [str]
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Bookmark
# ---------------------------------------------------------------------------

class Bookmark(Base):
    """
    Bookmarked learning resources.
    """
    __tablename__ = "cloudprep_bookmarks"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    url = Column(Text, nullable=False)
    resource_type = Column(String(40), default="article")  # article | video | lab | doc
    topic_name = Column(String(120), nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# AI Chat (Mentor)
# ---------------------------------------------------------------------------

class AIChat(Base):
    """
    Stored AI Mentor conversation messages.
    role: 'user' | 'assistant'
    """
    __tablename__ = "cloudprep_ai_chats"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=False)   # group messages in a session
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    topic_context = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Interview Attempt
# ---------------------------------------------------------------------------

class InterviewAttempt(Base):
    """
    One mock interview question+answer with AI scoring.
    """
    __tablename__ = "cloudprep_interview_attempts"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=False)
    topic = Column(String(120), nullable=True)
    difficulty = Column(String(20), default="medium")  # easy | medium | hard
    question = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)   # 0–100
    xp_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Achievement / Gamification
# ---------------------------------------------------------------------------

class Achievement(Base):
    """
    Earned badges and XP log entries.
    type: 'badge' | 'xp'
    """
    __tablename__ = "cloudprep_achievements"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    achievement_type = Column(String(20), nullable=False, default="xp")
    badge_id = Column(String(60), nullable=True)    # slug for badge
    badge_name = Column(String(120), nullable=True)
    badge_icon = Column(String(10), nullable=True)
    xp_amount = Column(Integer, default=0)
    description = Column(String(300), nullable=True)
    earned_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Certification
# ---------------------------------------------------------------------------

class Certification(Base):
    """
    Cloud certification tracker.
    """
    __tablename__ = "cloudprep_certifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    cert_id = Column(String(60), nullable=False)
    cert_name = Column(String(200), nullable=False)
    provider = Column(String(60), default="AWS")
    status = Column(String(20), default="planned")
    target_date = Column(String(10), nullable=True)
    passed_date = Column(String(10), nullable=True)
    score = Column(Integer, nullable=True)
    cost_usd = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
