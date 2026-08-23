import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


STATUS_FLOW = ["drafted", "reviewed", "submitted", "interviewing", "offered", "rejected"]


class Application(Base):
    """
    The join between a job and the specific resume version used.
    One row per application event. Multiple applications can point to same job
    (if user applies again) or same resume (if it's reused).
    """
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=False)

    # drafted → reviewed → submitted → interviewing → offered / rejected
    status = Column(String(30), nullable=False, default="drafted")

    # Set when status transitions to "submitted"
    applied_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)

    last_status_change = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApplicationEvent(Base):
    """
    Immutable audit log of every status transition.
    Powers the timeline view in the UI.
    """
    __tablename__ = "application_events"

    id = Column(String(36), primary_key=True, default=_uuid)

    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)
    status = Column(String(30), nullable=False)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
