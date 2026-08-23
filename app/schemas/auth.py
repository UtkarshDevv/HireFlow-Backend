from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

try:
    from pydantic import EmailStr
except ImportError:
    EmailStr = str


class UserSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name of the user")
    email: str = Field(..., min_length=5, max_length=120, description="Valid user email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password with min 6 characters")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User registered email")
    password: str = Field(..., description="User password")


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
