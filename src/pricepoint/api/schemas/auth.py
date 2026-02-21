"""Pydantic models for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            msg = "Password must be at least 8 characters"
            raise ValueError(msg)
        return v


class LoginRequest(BaseModel):
    """Request body for JSON-based login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user profile returned by API."""

    id: int
    email: str
    display_name: str | None = None
    is_active: bool
    is_admin: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request body for updating user profile."""

    display_name: str | None = None


class TokenResponse(BaseModel):
    """JWT token response from login."""

    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """JWT token + user profile returned on login/register."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
