import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Profile(Base):
    """
    Single structured profile for the user.
    All data stored as JSON blobs — structured, not free text.
    This makes re-use and LLM tailoring easy.
    """
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)

    # { name, email, phone, location, linkedin, github, website, summary }
    contact = Column(JSON, nullable=False, default=dict)

    # [{ school, degree, field, start_date, end_date, gpa, highlights: [] }]
    education = Column(JSON, nullable=False, default=list)

    # [{ company, title, location, start_date, end_date, current, bullets: [] }]
    experience = Column(JSON, nullable=False, default=list)

    # [{ name, description, bullets: [], url, tech_stack: [], start_date, end_date }]
    projects = Column(JSON, nullable=False, default=list)

    # [{ name, issuer, date, url, credential_id }]
    certifications = Column(JSON, nullable=False, default=list)

    # [{ name, category, proficiency, years }]
    # proficiency: beginner | intermediate | advanced | expert
    skills = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
