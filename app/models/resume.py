import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Resume(Base):
    """
    A resume version — either the base master resume or a tailored version for a specific job.
    job_id == NULL  →  base/master resume.
    job_id != NULL  →  tailored for that job.

    Multiple tailored versions can exist for the same job (each is a new row).
    The application row tracks which exact version was used.
    """
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=True, index=True)

    # NULL for base resume; FK to jobs for tailored
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=True)

    # 'clean_ats' | 'modern' | 'technical'
    template_id = Column(String(50), nullable=False, default="clean_ats")

    # Structured resume content — same shape as Profile but reordered/rewritten
    # {
    #   contact: {...},
    #   summary: "...",
    #   experience: [...],
    #   education: [...],
    #   skills: [...],
    #   projects: [...],
    #   certifications: [...]
    # }
    content = Column(JSON, nullable=False)

    # Path to the generated .docx or .pdf file on disk
    file_path = Column(Text, nullable=True)

    # Human-readable note: "tailored for backend keywords", "base resume"
    version_note = Column(Text, nullable=True)

    # Tailoring metadata — what the LLM changed
    # { keywords_matched: [], keywords_missing: [], match_score: 80 }
    tailoring_meta = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
