import uuid
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, DateTime, JSON, Text
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    """
    A job posting — either manually pasted or fetched from an API.
    Kept as-is with raw description for re-tailoring.
    """
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)

    # Source identifier: 'manual', 'adzuna', 'remoteok', 'usajobs', 'linkedin_manual'
    source = Column(String(50), nullable=False, default="manual")
    source_url = Column(Text, nullable=True)

    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)

    # Full JD text — preserved for re-tailoring
    description_raw = Column(Text, nullable=False)

    # Skills + requirements extracted by LLM from the JD
    # { required_skills: [], preferred_skills: [], action_verbs: [], seniority: '' }
    extracted_keywords = Column(JSON, nullable=True)

    # 0–100 match score against current profile
    match_score = Column(String(10), nullable=True)

    # Optional projects attached specifically to this job/application
    # [{ name: '', url: '', bullets: ['point 1', 'point 2'], tech_stack: [] }]
    projects = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
