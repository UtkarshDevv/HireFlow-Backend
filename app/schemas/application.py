from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ApplicationCreate(BaseModel):
    job_id: str
    resume_id: str
    notes: str = ""


class StatusUpdate(BaseModel):
    status: str  # drafted|reviewed|submitted|interviewing|offered|rejected
    note: str = ""


class ApplicationEventOut(BaseModel):
    id: str
    application_id: str
    status: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    resume_id: str
    status: str
    applied_at: Optional[datetime]
    notes: Optional[str]
    last_status_change: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationDetail(ApplicationOut):
    """Full detail — includes denormalized job/resume info + event timeline."""
    job: Optional[dict] = None
    resume: Optional[dict] = None
    events: List[ApplicationEventOut] = []
