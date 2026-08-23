from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileOut
from app.routers.auth import get_optional_current_user

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _get_profile(db: Session, user: Optional[User] = None) -> Profile | None:
    """Return user's isolated profile."""
    if user:
        p = db.query(Profile).filter(Profile.user_id == user.id).first()
        if p:
            return p
    # Fallback to first profile if not found or no user specified
    return db.query(Profile).first()


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """Create the user's isolated profile (replaces existing if one exists)."""
    existing = _get_profile(db, user)
    if existing:
        # Update instead of creating duplicate
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        if user and not existing.user_id:
            existing.user_id = user.id
        db.commit()
        db.refresh(existing)
        return existing

    profile_data = payload.model_dump()
    if user:
        profile_data["user_id"] = user.id
    profile = Profile(**profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    profile = _get_profile(db, user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    return profile


@router.patch("/me", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    profile = _get_profile(db, user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    if user and not profile.user_id:
        profile.user_id = user.id

    db.commit()
    db.refresh(profile)
    return profile
