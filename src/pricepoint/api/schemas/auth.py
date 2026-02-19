"""Pydantic models for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str
    display_name: str | None = None


class UserResponse(BaseModel):
    """Public user profile returned by API."""

    id: int
    email: str
    display_name: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request body for updating user profile."""

    display_name: str | None = None


class TokenResponse(BaseModel):
    """JWT token response from login."""

    access_token: str
    token_type: str = "bearer"
