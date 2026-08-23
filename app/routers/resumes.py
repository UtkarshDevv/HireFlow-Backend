from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resume import Resume
from app.models.profile import Profile
from app.models.job import Job
from app.models.user import User
from app.routers.auth import get_optional_current_user
from app.schemas.resume import ResumeOut, TailorRequest
from app.services import tailoring as tailoring_svc
from app.services import pdf_generator

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _get_resume_filename(resume: Resume, ext: str, db: Session) -> str:
    """Generate a clean, professional filename containing the user's name (e.g. John_Doe_Resume.pdf)."""
    candidate_name = None

    # 1. Try from resume content contact block
    if resume.content and isinstance(resume.content, dict):
        contact = resume.content.get("contact", {})
        if isinstance(contact, dict) and contact.get("name"):
            candidate_name = str(contact["name"]).strip()

    # 2. Try from user record
    if not candidate_name and resume.user_id:
        user = db.query(User).filter(User.id == resume.user_id).first()
        if user and user.name:
            candidate_name = user.name.strip()

    # 3. Try from profile contact block
    if not candidate_name:
        profile = db.query(Profile).first()
        if profile and profile.contact and isinstance(profile.contact, dict) and profile.contact.get("name"):
            candidate_name = str(profile.contact["name"]).strip()

    if candidate_name:
        safe_name = re.sub(r"[^\w\s-]", "", candidate_name).strip()
        safe_name = re.sub(r"[\s_]+", "_", safe_name)
    else:
        safe_name = "Candidate"

    # Optional: If tailored for a specific job, append company name
    if resume.job_id:
        job = db.query(Job).filter(Job.id == resume.job_id).first()
        if job and job.company:
            safe_company = re.sub(r"[^\w\s-]", "", job.company).strip()
            safe_company = re.sub(r"[\s_]+", "_", safe_company)
            return f"{safe_name}_Resume_{safe_company}.{ext}"

    return f"{safe_name}_Resume.{ext}"


@router.get("", response_model=List[ResumeOut])
def list_resumes(
    job_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(Resume)
    if user:
        q = q.filter((Resume.user_id == user.id) | (Resume.user_id.is_(None)))
    if job_id:
        q = q.filter(Resume.job_id == job_id)
    return q.order_by(Resume.created_at.desc()).all()


# ── Static routes MUST come before /{resume_id} wildcard ──────────────────

@router.post("/base", response_model=ResumeOut, status_code=201)
async def generate_base_resume(
    payload: TailorRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """Generate the base (master) resume from the user's profile."""
    if user:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first() or db.query(Profile).first()
    else:
        profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(400, "Complete your profile before generating a resume.")

    content = tailoring_svc.build_base_resume_content(profile)

    resume = Resume(
        user_id=user.id if user else None,
        job_id=None,
        template_id=payload.template_id,
        content=content,
        version_note=payload.version_note or "Base resume",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Generate DOCX and PDF files
    file_path = await pdf_generator.generate_docx(resume.id, content, payload.template_id)
    await pdf_generator.generate_pdf(resume.id, content, payload.template_id)
    resume.file_path = file_path
    db.commit()
    db.refresh(resume)
    return resume


# ── Dynamic /{resume_id} routes ────────────────────────────────────────────

@router.get("/{resume_id}/download")
def download_resume(resume_id: str, db: Session = Depends(get_db)):
    """Serve the exact DOCX file tied to this resume version with user's name."""
    resume = db.query(Resume).get(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    if not resume.file_path or not os.path.exists(resume.file_path):
        raise HTTPException(404, "File not generated yet. Call /resumes/base or /jobs/{id}/tailor first.")
    
    filename = _get_resume_filename(resume, "docx", db)
    return FileResponse(
        resume.file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/{resume_id}/download-pdf")
async def download_resume_pdf(resume_id: str, db: Session = Depends(get_db)):
    """Serve the exact PDF file tied to this resume version with user's name."""
    resume = db.query(Resume).get(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    # PDF path is same as docx but with .pdf extension
    pdf_path = resume.file_path.replace(".docx", ".pdf") if resume.file_path else None
    if not pdf_path or not os.path.exists(pdf_path):
        # Generate on the fly if it doesn't exist
        try:
            pdf_path = await pdf_generator.generate_pdf(resume.id, resume.content, resume.template_id)
        except Exception as e:
            raise HTTPException(500, f"Failed to generate PDF: {str(e)}")
            
    filename = _get_resume_filename(resume, "pdf", db)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).get(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).get(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    db.delete(resume)
    db.commit()
