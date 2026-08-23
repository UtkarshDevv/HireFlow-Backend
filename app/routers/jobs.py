from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.routers.auth import get_optional_current_user
from app.schemas.job import JobCreate, JobOut, JobFetchRequest
from app.schemas.resume import ResumeOut, TailorRequest
from app.services import tailoring as tailoring_svc
from app.services import job_aggregator
from app.services import pdf_generator
from app.models.resume import Resume

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """Manually add a job (paste JD text)."""
    job_data = payload.model_dump()
    if user:
        job_data["user_id"] = user.id
    job = Job(**job_data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=List[JobOut])
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(Job)
    if user:
        q = q.filter((Job.user_id == user.id) | (Job.user_id.is_(None)))
    if source:
        q = q.filter(Job.source == source)
    return q.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()


# ── Static routes MUST come before /{job_id} wildcard ──────────────────────

@router.post("/fetch", response_model=List[JobOut])
async def fetch_jobs(payload: JobFetchRequest, db: Session = Depends(get_db)):
    """Fetch jobs from external APIs (Adzuna, RemoteOK, etc.)."""
    fetched = await job_aggregator.fetch_jobs(
        query=payload.query,
        location=payload.location,
        sources=payload.sources,
        max_results=payload.max_results,
    )
    created = []
    for item in fetched:
        job = Job(**item)
        db.add(job)
        created.append(job)
    db.commit()
    for job in created:
        db.refresh(job)
    return created


# ── Dynamic /{job_id} routes ───────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()


@router.post("/{job_id}/extract-keywords", response_model=JobOut)
async def extract_keywords(job_id: str, db: Session = Depends(get_db)):
    """Run LLM keyword extraction on the job's raw description."""
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    profile = db.query(Profile).first()
    keywords, score = await tailoring_svc.extract_keywords_and_score(
        job.description_raw,
        profile.skills if profile else []
    )
    job.extracted_keywords = keywords
    job.match_score = str(score)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/tailor", response_model=ResumeOut, status_code=201)
async def tailor_resume(
    job_id: str,
    payload: TailorRequest,
    db: Session = Depends(get_db),
):
    """Run LLM tailoring for a specific job → creates a new Resume row."""
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(400, "Complete your profile before tailoring.")

    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    custom_projects = None
    if payload.projects is not None:
        custom_projects = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in payload.projects]
    elif job.projects:
        custom_projects = job.projects

    tailored_content, meta = await tailoring_svc.tailor_resume(
        profile=profile,
        job_description=job.description_raw,
        extracted_keywords=job.extracted_keywords,
        custom_projects=custom_projects,
    )

    resume = Resume(
        job_id=job_id,
        template_id=payload.template_id,
        content=tailored_content,
        version_note=payload.version_note or f"Tailored for {job.company} – {job.title}",
        tailoring_meta=meta,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Generate DOCX and PDF
    file_path = await pdf_generator.generate_docx(resume.id, tailored_content, payload.template_id)
    await pdf_generator.generate_pdf(resume.id, tailored_content, payload.template_id, tailoring_meta=meta)
    resume.file_path = file_path
    db.commit()
    db.refresh(resume)

    # Update job match score
    if meta.get("match_score"):
        job.match_score = str(meta["match_score"])
        db.commit()

    return resume
