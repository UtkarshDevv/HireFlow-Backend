from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


from app.schemas.profile import ProjectEntry


class JobCreate(BaseModel):
    company: str
    title: str
    description_raw: str
    location: str = ""
    source: str = "manual"
    source_url: str = ""
    projects: Optional[List[ProjectEntry]] = []


class JobOut(BaseModel):
    id: str
    source: str
    source_url: Optional[str]
    company: str
    title: str
    location: Optional[str]
    description_raw: str
    extracted_keywords: Optional[Any]
    match_score: Optional[str]
    projects: Optional[Any] = []
    created_at: datetime

    class Config:
        from_attributes = True


class JobFetchRequest(BaseModel):
    """Trigger the job aggregator to fetch jobs from external APIs."""
    query: str  # job title / keywords
    location: str = "remote"
    sources: List[str] = ["adzuna", "remoteok"]
    max_results: int = 20
