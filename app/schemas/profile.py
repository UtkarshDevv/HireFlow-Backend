from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Sub-schemas ────────────────────────────────────────────────────────────────

class ContactInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    summary: str = ""


class EducationEntry(BaseModel):
    school: str = ""
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    highlights: List[str] = []


class ExperienceEntry(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    bullets: List[str] = []


class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""
    bullets: List[str] = []
    url: str = ""
    github_url: str = ""
    tech_stack: List[str] = []
    start_date: str = ""
    end_date: str = ""


class CertificationEntry(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""
    url: str = ""
    credential_id: str = ""


class SkillEntry(BaseModel):
    name: str = ""
    category: str = ""
    proficiency: str = "intermediate"  # beginner|intermediate|advanced|expert
    years: float = 0


# ── Profile CRUD schemas ────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    education: List[EducationEntry] = []
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    certifications: List[CertificationEntry] = []
    skills: List[SkillEntry] = []


class ProfileUpdate(BaseModel):
    contact: Optional[ContactInfo] = None
    education: Optional[List[EducationEntry]] = None
    experience: Optional[List[ExperienceEntry]] = None
    projects: Optional[List[ProjectEntry]] = None
    certifications: Optional[List[CertificationEntry]] = None
    skills: Optional[List[SkillEntry]] = None


class ProfileOut(BaseModel):
    id: str
    contact: Any
    education: Any
    experience: Any
    projects: Any
    certifications: Any
    skills: Any
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
