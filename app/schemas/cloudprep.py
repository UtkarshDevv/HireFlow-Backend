"""
CloudPrep AI — Pydantic schemas (request / response).
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── LearningTopic ────────────────────────────────────────────────────────────

class SubTopicItem(BaseModel):
    name: str
    progress_pct: float = 0.0
    order: int = 0
    completed: bool = False


class TopicCreate(BaseModel):
    name: str
    icon: str = "📘"
    color: str = "#6366f1"
    order: int = 0
    sub_topics: List[SubTopicItem] = []


class TopicUpdate(BaseModel):
    progress_pct: Optional[float] = None
    sub_topics: Optional[List[SubTopicItem]] = None
    total_study_minutes: Optional[int] = None


class TopicOut(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    order: int
    progress_pct: float
    sub_topics: List[Any]
    total_study_minutes: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── StudySession ─────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    duration_minutes: int = Field(30, ge=1, le=480)
    notes: Optional[str] = None
    session_date: str   # YYYY-MM-DD


class SessionOut(BaseModel):
    id: str
    topic_id: Optional[str]
    topic_name: Optional[str]
    duration_minutes: int
    xp_earned: int
    notes: Optional[str]
    session_date: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── DailyGoal ────────────────────────────────────────────────────────────────

class GoalOut(BaseModel):
    id: str
    goal_date: str
    target_minutes: int
    actual_minutes: int
    target_xp: int
    actual_xp: int
    completed: bool

    class Config:
        from_attributes = True


# ── Note ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    title: str
    content: str = ""
    tags: List[str] = []
    pinned: bool = False


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    pinned: Optional[bool] = None


class NoteOut(BaseModel):
    id: str
    topic_id: Optional[str]
    topic_name: Optional[str]
    title: str
    content: str
    tags: List[Any]
    pinned: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Bookmark ─────────────────────────────────────────────────────────────────

class BookmarkCreate(BaseModel):
    title: str
    url: str
    resource_type: str = "article"
    topic_name: Optional[str] = None
    tags: List[str] = []


class BookmarkOut(BaseModel):
    id: str
    title: str
    url: str
    resource_type: str
    topic_name: Optional[str]
    tags: List[Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ── AIChat ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # user | assistant
    content: str


class MentorRequest(BaseModel):
    session_id: str
    message: str
    topic_context: Optional[str] = None
    history: List[ChatMessage] = []


class MentorResponse(BaseModel):
    session_id: str
    reply: str
    topic_context: Optional[str]


class ChatOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    topic_context: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── InterviewAttempt ─────────────────────────────────────────────────────────

class InterviewStartRequest(BaseModel):
    topic: Optional[str] = None
    difficulty: str = "medium"


class InterviewQuestionOut(BaseModel):
    session_id: str
    attempt_id: str
    question: str
    topic: Optional[str]
    difficulty: str


class InterviewAnswerRequest(BaseModel):
    attempt_id: str
    answer: str


class InterviewAttemptOut(BaseModel):
    id: str
    session_id: str
    topic: Optional[str]
    difficulty: str
    question: str
    user_answer: Optional[str]
    ai_feedback: Optional[str]
    score: Optional[int]
    xp_earned: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Achievement ───────────────────────────────────────────────────────────────

class AchievementOut(BaseModel):
    id: str
    achievement_type: str
    badge_id: Optional[str]
    badge_name: Optional[str]
    badge_icon: Optional[str]
    xp_amount: int
    description: Optional[str]
    earned_at: datetime

    class Config:
        from_attributes = True


class UserStatsOut(BaseModel):
    total_xp: int
    level: int
    level_name: str
    xp_to_next: int
    current_streak: int
    longest_streak: int
    total_study_minutes: int
    total_sessions: int
    badges_earned: int
    topics_completed: int


# ── Certification ─────────────────────────────────────────────────────────────

class CertCreate(BaseModel):
    name: str
    provider: Optional[str] = None
    level: Optional[str] = None
    status: str = "planned"
    target_date: Optional[str] = None
    passed_date: Optional[str] = None
    credential_url: Optional[str] = None
    progress_pct: float = 0.0
    exam_topics: List[Any] = []
    notes: Optional[str] = None


class CertUpdate(BaseModel):
    status: Optional[str] = None
    target_date: Optional[str] = None
    passed_date: Optional[str] = None
    credential_url: Optional[str] = None
    progress_pct: Optional[float] = None
    exam_topics: Optional[List[Any]] = None
    notes: Optional[str] = None


class CertOut(BaseModel):
    id: str
    name: str
    provider: Optional[str]
    level: Optional[str]
    status: str
    target_date: Optional[str]
    passed_date: Optional[str]
    credential_url: Optional[str]
    progress_pct: float
    exam_topics: List[Any]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Dashboard aggregate ───────────────────────────────────────────────────────

class CloudPrepDashboardOut(BaseModel):
    total_xp: int
    level: int
    level_name: str
    current_streak: int
    ai_readiness_score: float
    overall_progress_pct: float
    today_minutes: int
    weekly_minutes: int
    total_sessions: int
    topics: List[TopicOut]
    today_goal: Optional[GoalOut]
    recent_sessions: List[SessionOut]
    badges_count: int
    certs_in_progress: int
