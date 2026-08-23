"""
CloudPrep AI — FastAPI router.
Prefix: /cloudprep
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_optional_current_user
from app.models.cloudprep import (
    LearningTopic, StudySession, DailyGoal,
    Note, Bookmark, AIChat, InterviewAttempt,
    Achievement, Certification,
)
from app.schemas.cloudprep import (
    TopicCreate, TopicUpdate, TopicOut,
    SessionCreate, SessionOut,
    GoalOut,
    NoteCreate, NoteUpdate, NoteOut,
    BookmarkCreate, BookmarkOut,
    MentorRequest, MentorResponse,
    InterviewStartRequest, InterviewQuestionOut,
    InterviewAnswerRequest, InterviewAttemptOut,
    AchievementOut, UserStatsOut,
    CertCreate, CertUpdate, CertOut,
    CloudPrepDashboardOut,
)
from app.services.cloudprep_ai import (
    mentor_reply, generate_interview_question,
    score_interview_answer, calc_session_xp, calc_interview_xp,
    get_level_info, calc_streak,
)

router = APIRouter(prefix="/cloudprep", tags=["cloudprep"])

# ── Seed data ─────────────────────────────────────────────────────────────────

DEFAULT_TOPICS = [
    {"name": "Linux Fundamentals", "icon": "🐧", "color": "#f59e0b", "order": 1,
     "sub_topics": [
         {"name": "File System & Navigation", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Process Management", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "Permissions & Users", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "Networking Basics", "progress_pct": 0, "order": 4, "completed": False},
         {"name": "Shell Scripting", "progress_pct": 0, "order": 5, "completed": False},
     ]},
    {"name": "AWS Core Services", "icon": "☁️", "color": "#f97316", "order": 2,
     "sub_topics": [
         {"name": "IAM & Security", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "EC2 & Auto Scaling", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "VPC & Networking", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "S3 & Storage", "progress_pct": 0, "order": 4, "completed": False},
         {"name": "RDS & DynamoDB", "progress_pct": 0, "order": 5, "completed": False},
         {"name": "Lambda & Serverless", "progress_pct": 0, "order": 6, "completed": False},
     ]},
    {"name": "Docker", "icon": "🐳", "color": "#0ea5e9", "order": 3,
     "sub_topics": [
         {"name": "Images & Containers", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Dockerfile Best Practices", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "Docker Compose", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "Networking & Volumes", "progress_pct": 0, "order": 4, "completed": False},
         {"name": "Registry & Security", "progress_pct": 0, "order": 5, "completed": False},
     ]},
    {"name": "Kubernetes", "icon": "⚓", "color": "#6366f1", "order": 4,
     "sub_topics": [
         {"name": "Pods & Deployments", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Services & Ingress", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "ConfigMaps & Secrets", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "Persistent Volumes", "progress_pct": 0, "order": 4, "completed": False},
         {"name": "RBAC & Security", "progress_pct": 0, "order": 5, "completed": False},
         {"name": "Helm & GitOps", "progress_pct": 0, "order": 6, "completed": False},
     ]},
    {"name": "Terraform", "icon": "🏗️", "color": "#8b5cf6", "order": 5,
     "sub_topics": [
         {"name": "HCL & Providers", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "State Management", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "Modules", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "Workspaces & Backends", "progress_pct": 0, "order": 4, "completed": False},
     ]},
    {"name": "CI/CD", "icon": "🔄", "color": "#10b981", "order": 6,
     "sub_topics": [
         {"name": "GitHub Actions", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Jenkins Pipelines", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "GitOps with ArgoCD", "progress_pct": 0, "order": 3, "completed": False},
         {"name": "Testing & Quality Gates", "progress_pct": 0, "order": 4, "completed": False},
     ]},
    {"name": "Networking", "icon": "🌐", "color": "#22d3ee", "order": 7,
     "sub_topics": [
         {"name": "TCP/IP & DNS", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Load Balancers & Proxies", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "VPN & VPC Peering", "progress_pct": 0, "order": 3, "completed": False},
     ]},
    {"name": "Security & SRE", "icon": "🛡️", "color": "#f43f5e", "order": 8,
     "sub_topics": [
         {"name": "Zero Trust & IAM", "progress_pct": 0, "order": 1, "completed": False},
         {"name": "Observability (Prometheus/Grafana)", "progress_pct": 0, "order": 2, "completed": False},
         {"name": "Incident Response", "progress_pct": 0, "order": 3, "completed": False},
     ]},
]

DEFAULT_CERTS = [
    {"name": "AWS Solutions Architect – Associate", "provider": "AWS", "level": "Associate", "status": "planned"},
    {"name": "Certified Kubernetes Administrator (CKA)", "provider": "CNCF", "level": "Professional", "status": "planned"},
    {"name": "HashiCorp Certified: Terraform Associate", "provider": "HashiCorp", "level": "Associate", "status": "planned"},
    {"name": "AWS DevOps Engineer – Professional", "provider": "AWS", "level": "Professional", "status": "planned"},
]


def _seed_topics(db: Session):
    """Seed topics from CourseDay if exists, else default topics."""
    from app.models.course import CourseDay
    from app.routers.course import sync_topics_from_course

    course_count = db.query(CourseDay).count()
    if course_count > 0:
        sync_topics_from_course(db)
        return

    existing = db.query(LearningTopic).count()
    if existing == 0:
        for t in DEFAULT_TOPICS:
            db.add(LearningTopic(**t))
        db.commit()


def _seed_certs(db: Session):
    """Seed default certifications if none exist."""
    existing = db.query(Certification).count()
    if existing == 0:
        for c in DEFAULT_CERTS:
            db.add(Certification(**c))
        db.commit()


# ── Helper: aggregate XP ──────────────────────────────────────────────────────

def _total_xp(db: Session) -> int:
    rows = db.query(Achievement.xp_amount).all()
    return sum(r[0] for r in rows)


def _add_xp(db: Session, amount: int, description: str):
    if amount > 0:
        db.add(Achievement(
            achievement_type="xp",
            xp_amount=amount,
            description=description,
        ))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=CloudPrepDashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    _seed_topics(db)
    _seed_certs(db)

    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    topics = db.query(LearningTopic).order_by(LearningTopic.order).all()
    today_sessions = db.query(StudySession).filter(StudySession.session_date == today).all()
    week_sessions = db.query(StudySession).filter(StudySession.session_date >= week_ago).all()
    all_sessions = db.query(StudySession).order_by(StudySession.created_at.desc()).all()
    today_goal = db.query(DailyGoal).filter(DailyGoal.goal_date == today).first()
    badges_count = db.query(Achievement).filter(Achievement.achievement_type == "badge").count()
    certs_in_progress = db.query(Certification).filter(Certification.status == "studying").count()

    total_xp = _total_xp(db)
    level_info = get_level_info(total_xp)

    session_dates = [s.session_date for s in all_sessions]
    current_streak, _ = calc_streak(session_dates)

    overall_pct = (
        sum(t.progress_pct for t in topics) / len(topics) if topics else 0.0
    )
    ai_readiness = min(100.0, overall_pct * 0.7 + min(total_xp / 100, 30))

    return CloudPrepDashboardOut(
        total_xp=total_xp,
        level=level_info["level"],
        level_name=level_info["level_name"],
        current_streak=current_streak,
        ai_readiness_score=round(ai_readiness, 1),
        overall_progress_pct=round(overall_pct, 1),
        today_minutes=sum(s.duration_minutes for s in today_sessions),
        weekly_minutes=sum(s.duration_minutes for s in week_sessions),
        total_sessions=len(all_sessions),
        topics=topics,
        today_goal=today_goal,
        recent_sessions=all_sessions[:5],
        badges_count=badges_count,
        certs_in_progress=certs_in_progress,
    )


# ── Topics ────────────────────────────────────────────────────────────────────

@router.get("/topics", response_model=List[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    _seed_topics(db)
    return db.query(LearningTopic).order_by(LearningTopic.order).all()


@router.post("/topics", response_model=TopicOut, status_code=201)
def create_topic(body: TopicCreate, db: Session = Depends(get_db)):
    topic = LearningTopic(**body.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: str, body: TopicUpdate, db: Session = Depends(get_db)):
    topic = db.query(LearningTopic).filter(LearningTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(topic, k, v)
    topic.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(topic)
    return topic


# ── Study Sessions ────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    topic_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(StudySession)
    if topic_id:
        q = q.filter(StudySession.topic_id == topic_id)
    return q.order_by(StudySession.created_at.desc()).limit(limit).all()


@router.post("/sessions", response_model=SessionOut, status_code=201)
def log_session(body: SessionCreate, db: Session = Depends(get_db)):
    xp = calc_session_xp(body.duration_minutes)
    session = StudySession(
        **body.model_dump(),
        xp_earned=xp,
    )
    db.add(session)

    # Update topic study time
    if body.topic_id:
        topic = db.query(LearningTopic).filter(LearningTopic.id == body.topic_id).first()
        if topic:
            topic.total_study_minutes = (topic.total_study_minutes or 0) + body.duration_minutes

    # Update daily goal
    goal = db.query(DailyGoal).filter(DailyGoal.goal_date == body.session_date).first()
    if not goal:
        goal = DailyGoal(goal_date=body.session_date, target_minutes=60, target_xp=100)
        db.add(goal)
    goal.actual_minutes = (goal.actual_minutes or 0) + body.duration_minutes
    goal.actual_xp = (goal.actual_xp or 0) + xp
    goal.completed = goal.actual_minutes >= goal.target_minutes

    # Award XP
    _add_xp(db, xp, f"Study session: {body.topic_name or 'General'} ({body.duration_minutes} min)")

    # Check streak badge
    all_dates = [s.session_date for s in db.query(StudySession).all()]
    all_dates.append(body.session_date)
    streak, _ = calc_streak(all_dates)
    _check_streak_badges(db, streak)

    db.commit()
    db.refresh(session)
    return session


def _check_streak_badges(db: Session, streak: int):
    milestones = {3: ("streak_3", "3-Day Streak", "🔥"), 7: ("streak_7", "7-Day Streak", "🔥"), 30: ("streak_30", "30-Day Streak", "💎")}
    for days, (badge_id, name, icon) in milestones.items():
        if streak == days:
            existing = db.query(Achievement).filter(
                Achievement.badge_id == badge_id
            ).first()
            if not existing:
                db.add(Achievement(
                    achievement_type="badge",
                    badge_id=badge_id, badge_name=name, badge_icon=icon,
                    xp_amount=days * 10,
                    description=f"Studied {days} days in a row!",
                ))


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/notes", response_model=List[NoteOut])
def list_notes(
    topic_id: Optional[str] = None,
    pinned: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Note)
    if topic_id:
        q = q.filter(Note.topic_id == topic_id)
    if pinned is not None:
        q = q.filter(Note.pinned == pinned)
    return q.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()


@router.post("/notes", response_model=NoteOut, status_code=201)
def create_note(body: NoteCreate, db: Session = Depends(get_db)):
    note = Note(**body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: str, body: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(note, k, v)
    note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: str, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if note:
        db.delete(note)
        db.commit()


# ── Bookmarks ─────────────────────────────────────────────────────────────────

@router.get("/bookmarks", response_model=List[BookmarkOut])
def list_bookmarks(
    topic_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(Bookmark)
    if user:
        q = q.filter((Bookmark.user_id == user.id) | (Bookmark.user_id.is_(None)))
    if topic_name:
        q = q.filter(Bookmark.topic_name == topic_name)
    if resource_type:
        q = q.filter(Bookmark.resource_type == resource_type)
    return q.order_by(Bookmark.created_at.desc()).all()


@router.post("/bookmarks", response_model=BookmarkOut, status_code=201)
def create_bookmark(
    body: BookmarkCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    bm_data = body.model_dump()
    if user:
        bm_data["user_id"] = user.id
    bm = Bookmark(**bm_data)
    db.add(bm)
    db.commit()
    db.refresh(bm)
    return bm


@router.delete("/bookmarks/{bm_id}", status_code=204)
def delete_bookmark(bm_id: str, db: Session = Depends(get_db)):
    bm = db.query(Bookmark).filter(Bookmark.id == bm_id).first()
    if bm:
        db.delete(bm)
        db.commit()


# ── AI Mentor Chat ────────────────────────────────────────────────────────────

@router.post("/mentor", response_model=MentorResponse)
def chat_with_mentor(body: MentorRequest, db: Session = Depends(get_db)):
    # Persist user message
    db.add(AIChat(
        session_id=body.session_id,
        role="user",
        content=body.message,
        topic_context=body.topic_context,
    ))

    history = [{"role": m.role, "content": m.content} for m in body.history]
    reply = mentor_reply(body.message, history, body.topic_context)

    # Persist assistant reply
    db.add(AIChat(
        session_id=body.session_id,
        role="assistant",
        content=reply,
        topic_context=body.topic_context,
    ))

    # 5 XP per question asked
    _add_xp(db, 5, "AI Mentor question")
    db.commit()

    return MentorResponse(
        session_id=body.session_id,
        reply=reply,
        topic_context=body.topic_context,
    )


@router.get("/mentor/history/{session_id}")
def get_mentor_history(session_id: str, db: Session = Depends(get_db)):
    msgs = db.query(AIChat).filter(
        AIChat.session_id == session_id
    ).order_by(AIChat.created_at.asc()).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs]


# ── AI Interviewer ────────────────────────────────────────────────────────────

@router.post("/interview/start", response_model=InterviewQuestionOut)
def start_interview(body: InterviewStartRequest, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    data = generate_interview_question(body.topic, body.difficulty)

    attempt = InterviewAttempt(
        session_id=session_id,
        topic=body.topic,
        difficulty=body.difficulty,
        question=data["question"],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return InterviewQuestionOut(
        session_id=session_id,
        attempt_id=attempt.id,
        question=attempt.question,
        topic=attempt.topic,
        difficulty=attempt.difficulty,
    )


@router.post("/interview/answer", response_model=InterviewAttemptOut)
def submit_answer(body: InterviewAnswerRequest, db: Session = Depends(get_db)):
    attempt = db.query(InterviewAttempt).filter(InterviewAttempt.id == body.attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Interview attempt not found")

    result = score_interview_answer(attempt.question, body.answer, attempt.topic)
    xp = calc_interview_xp(result["score"])

    attempt.user_answer = body.answer
    attempt.score = result["score"]
    attempt.ai_feedback = (
        f"**Score: {result['score']}/100**\n\n"
        f"✅ **Strengths**: {', '.join(result['strengths'])}\n\n"
        f"📈 **Improve**: {', '.join(result['improvements'])}\n\n"
        f"💡 **Model Answer**: {result['model_answer']}"
    )
    attempt.xp_earned = xp

    _add_xp(db, xp, f"Mock interview ({attempt.topic}, score {result['score']})")

    # Badge: first perfect score
    if result["score"] >= 90:
        existing = db.query(Achievement).filter(Achievement.badge_id == "perfect_interview").first()
        if not existing:
            db.add(Achievement(
                achievement_type="badge",
                badge_id="perfect_interview", badge_name="Interview Ace", badge_icon="🎯",
                xp_amount=50,
                description="Scored 90+ on a mock interview!",
            ))

    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/interview/history", response_model=List[InterviewAttemptOut])
def interview_history(
    topic: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(InterviewAttempt)
    if topic:
        q = q.filter(InterviewAttempt.topic == topic)
    return q.order_by(InterviewAttempt.created_at.desc()).limit(limit).all()


# ── Achievements ──────────────────────────────────────────────────────────────

@router.get("/achievements/stats", response_model=UserStatsOut)
def get_user_stats(db: Session = Depends(get_db)):
    total_xp = _total_xp(db)
    level_info = get_level_info(total_xp)

    all_sessions = db.query(StudySession).all()
    session_dates = [s.session_date for s in all_sessions]
    current_streak, longest_streak = calc_streak(session_dates)

    topics = db.query(LearningTopic).all()
    topics_completed = sum(1 for t in topics if t.progress_pct >= 100)

    return UserStatsOut(
        total_xp=total_xp,
        level=level_info["level"],
        level_name=level_info["level_name"],
        xp_to_next=level_info["xp_to_next"],
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_study_minutes=sum(s.duration_minutes for s in all_sessions),
        total_sessions=len(all_sessions),
        badges_earned=db.query(Achievement).filter(Achievement.achievement_type == "badge").count(),
        topics_completed=topics_completed,
    )


@router.get("/achievements", response_model=List[AchievementOut])
def list_achievements(db: Session = Depends(get_db)):
    return (
        db.query(Achievement)
        .order_by(Achievement.earned_at.desc())
        .all()
    )


# ── Certifications ────────────────────────────────────────────────────────────

@router.get("/certifications", response_model=List[CertOut])
def list_certs(db: Session = Depends(get_db)):
    _seed_certs(db)
    return db.query(Certification).order_by(Certification.created_at).all()


@router.post("/certifications", response_model=CertOut, status_code=201)
def create_cert(body: CertCreate, db: Session = Depends(get_db)):
    cert = Certification(**body.model_dump())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.patch("/certifications/{cert_id}", response_model=CertOut)
def update_cert(cert_id: str, body: CertUpdate, db: Session = Depends(get_db)):
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        raise HTTPException(404, "Certification not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cert, k, v)
    cert.updated_at = datetime.utcnow()

    # Badge for passing a cert
    if body.status == "passed":
        existing = db.query(Achievement).filter(Achievement.badge_id == f"cert_{cert_id}").first()
        if not existing:
            db.add(Achievement(
                achievement_type="badge",
                badge_id=f"cert_{cert_id}",
                badge_name=f"Certified: {cert.name[:30]}",
                badge_icon="🏆",
                xp_amount=500,
                description=f"Passed {cert.name}!",
            ))
            _add_xp(db, 500, f"Certification passed: {cert.name}")

    db.commit()
    db.refresh(cert)
    return cert


@router.delete("/certifications/{cert_id}", status_code=204)
def delete_cert(cert_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if cert:
        db.delete(cert)
        db.commit()


# ── Daily Goal ────────────────────────────────────────────────────────────────

@router.get("/goals/today", response_model=GoalOut)
def get_today_goal(db: Session = Depends(get_db)):
    today = date.today().isoformat()
    goal = db.query(DailyGoal).filter(DailyGoal.goal_date == today).first()
    if not goal:
        goal = DailyGoal(goal_date=today, target_minutes=60, target_xp=100)
        db.add(goal)
        db.commit()
        db.refresh(goal)
    return goal
