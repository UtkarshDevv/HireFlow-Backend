from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
from app.schemas.profile import ProjectEntry


class ResumeOut(BaseModel):
    id: str
    job_id: Optional[str]
    template_id: str
    content: Any
    file_path: Optional[str]
    version_note: Optional[str]
    tailoring_meta: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


class TailorRequest(BaseModel):
    """Request to tailor a resume for a specific job."""
    template_id: str = "clean_ats"
    version_note: str = ""
    projects: Optional[List[ProjectEntry]] = None
