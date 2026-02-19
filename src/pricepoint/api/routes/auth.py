"""Authentication endpoints: register, login, and user profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.auth import TokenResponse, UserCreate, UserResponse, UserUpdate
from pricepoint.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Create a new user account."""
    existing = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate and return a JWT access token."""
    user = db.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Return the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Update the current user's display name."""
    if body.display_name is not None:
        current_user.display_name = body.display_name
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
