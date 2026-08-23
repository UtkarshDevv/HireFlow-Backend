"""
Authentication and User Management Service implementing Object-Oriented Programming (OOPS) Principles.
Adheres to SOLID design principles: Single Responsibility, Open/Closed, Dependency Inversion.
"""
from __future__ import annotations
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any
import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.models.profile import Profile
from app.services.email_service import BaseEmailNotifier, email_notifier


# ==============================================================================
# 1. Password Security Manager (Encapsulation)
# ==============================================================================

class PasswordManager:
    """
    Encapsulates password hashing and verification using NIST-approved PBKDF2-HMAC-SHA256
    with cryptographic random salting (100,000 rounds).
    """

    ITERATIONS = 100_000
    ALGORITHM = "sha256"

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a plaintext password with a unique random salt."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            cls.ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.ITERATIONS,
        )
        return f"{salt}:{key.hex()}"

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        """Verify a plaintext password against a stored salt:hash string."""
        try:
            if not stored_hash or ":" not in stored_hash:
                return False
            salt, key_hex = stored_hash.split(":", 1)
            calculated = hashlib.pbkdf2_hmac(
                cls.ALGORITHM,
                password.encode("utf-8"),
                salt.encode("utf-8"),
                cls.ITERATIONS,
            )
            return secrets.compare_digest(calculated.hex(), key_hex)
        except Exception:
            return False


# ==============================================================================
# 2. Token Security Manager (Encapsulation)
# ==============================================================================

class TokenManager:
    """
    Encapsulates JWT creation, decoding, and cryptographic token verification.
    """

    def __init__(self, secret_key: Optional[str] = None, algorithm: Optional[str] = None):
        settings = get_settings()
        self._secret_key = secret_key or settings.jwt_secret
        self._algorithm = algorithm or settings.jwt_algorithm
        self._expire_minutes = settings.jwt_access_token_expire_minutes

    def create_access_token(self, user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """Generate a signed JWT access token."""
        delta = expires_delta or timedelta(minutes=self._expire_minutes)
        expire = datetime.utcnow() + delta
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> Optional[dict]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except jwt.PyJWTError:
            return None


# ==============================================================================
# 3. User Data Access Repository (Repository Pattern)
# ==============================================================================

class UserRepository:
    """
    Data Access Object (DAO) encapsulating all database interactions for the User model.
    """

    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Query user by primary key ID."""
        return self._db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Query user by unique email address (case-insensitive)."""
        clean_email = (email or "").strip().lower()
        return self._db.query(User).filter(User.email == clean_email).first()

    def create(self, name: str, email: str, hashed_password: str) -> User:
        """Persist a new User entity to the database."""
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            is_active=True,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def count(self) -> int:
        """Return total registered users."""
        return self._db.query(User).count()


# ==============================================================================
# 4. Auth Service Coordinator (Facade & Dependency Injection)
# ==============================================================================

class AuthService:
    """
    High-level Authentication Service implementing the Facade pattern.
    Coordinates User Repository, Password Manager, Token Manager, and Email Notification.
    """

    def __init__(
        self,
        db: Session,
        password_manager: type[PasswordManager] = PasswordManager,
        token_manager: Optional[TokenManager] = None,
        notifier: Optional[BaseEmailNotifier] = None,
    ):
        self._db = db
        self._user_repo = UserRepository(db)
        self._password_manager = password_manager
        self._token_manager = token_manager or TokenManager()
        self._notifier = notifier or email_notifier

    def register_user(self, name: str, email: str, raw_password: str) -> Tuple[User, str]:
        """
        Registers a new user, hashes password, initializes user seed profile,
        dispatches an email notification to the administrator, and returns (user, token).
        """
        clean_email = email.strip().lower()
        existing = self._user_repo.get_by_email(clean_email)
        if existing:
            raise ValueError("An account with this email address already exists. Please sign in.")

        # Hash password securely
        hashed = self._password_manager.hash_password(raw_password)

        # Create user entity
        user = self._user_repo.create(name=name, email=clean_email, hashed_password=hashed)

        # Provision a default user profile
        self._initialize_user_profile(user)

        # Dispatch async signup notification email to utkarshsinha2122@gmail.com
        try:
            self._notifier.send_signup_notification(name=user.name, email=user.email)
        except Exception:
            pass

        # Generate JWT token
        token = self._token_manager.create_access_token(user_id=user.id, email=user.email)
        return user, token

    def authenticate_user(self, email: str, raw_password: str) -> Tuple[User, str]:
        """
        Verifies user credentials and returns (user, access_token).
        """
        clean_email = email.strip().lower()
        user = self._user_repo.get_by_email(clean_email)
        if not user:
            raise ValueError("Invalid email or password.")

        if not self._password_manager.verify_password(raw_password, user.hashed_password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("This account has been deactivated. Please contact support.")

        token = self._token_manager.create_access_token(user_id=user.id, email=user.email)
        return user, token

    def get_user_from_token(self, token: str) -> Optional[User]:
        """
        Validates token and returns the corresponding User entity.
        """
        payload = self._token_manager.decode_access_token(token)
        if not payload or "sub" not in payload:
            return None
        user_id = payload["sub"]
        return self._user_repo.get_by_id(user_id)

    def _initialize_user_profile(self, user: User) -> None:
        """
        Provisions a default Profile record for the new user.
        """
        try:
            existing_profile = self._db.query(Profile).filter(Profile.user_id == user.id).first()
            if not existing_profile:
                starter_profile = Profile(
                    user_id=user.id,
                    contact={
                        "name": user.name,
                        "email": user.email,
                        "phone": "",
                        "location": "",
                        "linkedin": "",
                        "github": "",
                        "website": "",
                        "summary": f"Aspiring software engineer and technical specialist exploring new career opportunities.",
                    },
                    education=[],
                    experience=[],
                    projects=[],
                    certifications=[],
                    skills=[
                        {"name": "Python", "category": "Languages", "proficiency": "intermediate", "years": 1},
                        {"name": "Problem Solving", "category": "Soft Skills", "proficiency": "advanced", "years": 2},
                    ],
                )
                self._db.add(starter_profile)
                self._db.commit()
        except Exception:
            pass
