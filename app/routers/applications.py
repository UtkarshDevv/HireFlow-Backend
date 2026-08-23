from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.routers.auth import get_optional_current_user
from app.schemas.application import (
    ApplicationCreate, ApplicationOut, ApplicationDetail,
    StatusUpdate, ApplicationEventOut
)

router = APIRouter(prefix="/applications", tags=["applications"])

VALID_STATUSES = ["drafted", "reviewed", "submitted", "interviewing", "offered", "rejected"]


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """Link a job + resume version into an application record."""
    if not db.query(Job).get(payload.job_id):
        raise HTTPException(400, "Job not found")
    if not db.query(Resume).get(payload.resume_id):
        raise HTTPException(400, "Resume not found")

    app_data = payload.model_dump()
    if user:
        app_data["user_id"] = user.id
    app_obj = Application(**app_data)
    db.add(app_obj)
    db.commit()

    # Log the initial event
    db.add(ApplicationEvent(application_id=app_obj.id, status="drafted", note="Application created"))
    db.commit()
    db.refresh(app_obj)
    return app_obj


@router.get("", response_model=List[ApplicationOut])
def list_applications(
    status: Optional[str] = None,
    company: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(Application)
    if user:
        q = q.filter((Application.user_id == user.id) | (Application.user_id.is_(None)))
    if status:
        q = q.filter(Application.status == status)
    if company:
        q = q.join(Job, Application.job_id == Job.id).filter(
            Job.company.ilike(f"%{company}%")
        )
    return q.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()


# ── Static routes MUST come before /{application_id} wildcard ─────────────

@router.get("/stats/summary")
def get_stats(db: Session = Depends(get_db)):
    """Return counts by status for the dashboard summary cards."""
    total = db.query(Application).count()
    stats: dict = {"total": total}
    for s in VALID_STATUSES:
        stats[s] = db.query(Application).filter(Application.status == s).count()
    return stats


# ── Dynamic /{application_id} routes ──────────────────────────────────────

@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: str, db: Session = Depends(get_db)):
    """Full detail: application + job info + resume info + event timeline."""
    app_obj = db.query(Application).get(application_id)
    if not app_obj:
        raise HTTPException(404, "Application not found")

    job = db.query(Job).get(app_obj.job_id)
    resume = db.query(Resume).get(app_obj.resume_id)
    events = (
        db.query(ApplicationEvent)
        .filter(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at.asc())
        .all()
    )

    return ApplicationDetail(
        **ApplicationOut.model_validate(app_obj).model_dump(),
        job={
            "id": job.id, "company": job.company, "title": job.title,
            "location": job.location, "source_url": job.source_url,
            "description_raw": job.description_raw,
            "extracted_keywords": job.extracted_keywords,
        } if job else None,
        resume={
            "id": resume.id, "template_id": resume.template_id,
            "version_note": resume.version_note,
            "content": resume.content,
            "tailoring_meta": resume.tailoring_meta,
            "file_path": resume.file_path,
        } if resume else None,
        events=[ApplicationEventOut.model_validate(e) for e in events],
    )


@router.patch("/{application_id}/status", response_model=ApplicationOut)
def update_status(
    application_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

    app_obj = db.query(Application).get(application_id)
    if not app_obj:
        raise HTTPException(404, "Application not found")

    db.add(ApplicationEvent(
        application_id=app_obj.id,
        status=payload.status,
        note=payload.note,
    ))

    app_obj.status = payload.status
    app_obj.last_status_change = datetime.utcnow()

    if payload.status == "submitted" and not app_obj.applied_at:
        app_obj.applied_at = datetime.utcnow()

    db.commit()
    db.refresh(app_obj)
    return app_obj


@router.patch("/{application_id}/notes", response_model=ApplicationOut)
def update_notes(application_id: str, notes: str, db: Session = Depends(get_db)):
    app_obj = db.query(Application).get(application_id)
    if not app_obj:
        raise HTTPException(404, "Application not found")
    app_obj.notes = notes
    db.commit()
    db.refresh(app_obj)
    return app_obj


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: str, db: Session = Depends(get_db)):
    app_obj = db.query(Application).get(application_id)
    if not app_obj:
        raise HTTPException(404, "Application not found")
    db.query(ApplicationEvent).filter(
        ApplicationEvent.application_id == application_id
    ).delete()
    db.delete(app_obj)
    db.commit()
