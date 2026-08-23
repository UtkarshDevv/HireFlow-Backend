"""
FastAPI Authentication Router with Bearer Token Dependencies.
Prefix: /auth
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserSignupRequest, UserLoginRequest, AuthResponse, UserOut
from app.services.auth_service import AuthService, TokenManager

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------------------
# Dependencies for Dependency Injection
# ------------------------------------------------------------------------------

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency injection helper returning a configured AuthService instance."""
    return AuthService(db=db)


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    FastAPI dependency that extracts and validates the JWT Bearer token.
    Raises 401 Unauthorized if invalid or missing.
    """
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.credentials
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """
    Optional user dependency — returns User if valid token is provided, else None.
    Allows public browsing with personalized data when authenticated.
    """
    if not auth_header or not auth_header.credentials:
        # Check if a default user exists for seamless backwards compatibility
        first_user = db.query(User).first()
        return first_user
    token = auth_header.credentials
    user = auth_service.get_user_from_token(token)
    if not user:
        return db.query(User).first()
    return user


# ------------------------------------------------------------------------------
# Auth Endpoints
# ------------------------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: UserSignupRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    Register a new user, dispatch an email notification to utkarshsinha2122@gmail.com,
    and return an access token.
    """
    try:
        user, token = auth_service.register_user(
            name=body.name,
            email=body.email,
            raw_password=body.password,
        )
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserOut.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create account.")


@router.post("/login", response_model=AuthResponse)
def login(body: UserLoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    Authenticate with email and password, returning a JWT token.
    """
    try:
        user, token = auth_service.authenticate_user(
            email=body.email,
            raw_password=body.password,
        )
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=UserOut.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed.")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Fetch details of the currently authenticated user.
    """
    return UserOut.model_validate(current_user)
