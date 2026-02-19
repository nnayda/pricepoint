"""Authentication endpoints: register, login, user profile, and OAuth."""

import secrets
from typing import Annotated

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
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
from pricepoint.api.rate_limit import limiter
from pricepoint.api.schemas.auth import TokenResponse, UserCreate, UserResponse, UserUpdate
from pricepoint.config.settings import get_settings
from pricepoint.db.models import User

oauth = OAuth()


def _configure_oauth() -> None:
    """Register the Google OAuth client using application settings."""
    settings = get_settings()
    oauth.register(
        name="google",
        client_id=settings.oauth_google_client_id,
        client_secret=settings.oauth_google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().rate_limit_auth)
def register(
    request: Request,
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
@limiter.limit(get_settings().rate_limit_auth)
def login(
    request: Request,
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


# ---------- Google OAuth ----------


@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    _configure_oauth()
    settings = get_settings()
    redirect_uri = settings.oauth_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Handle the OAuth callback from Google.

    Exchanges the authorization code for tokens, fetches user info, then
    either logs in an existing user, links a Google account, or creates a
    new account.
    """
    _configure_oauth()

    try:
        token_data = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OAuth authentication failed: {exc}",
        ) from exc

    user_info = token_data.get("userinfo")
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve user info from Google",
        )

    google_email: str | None = user_info.get("email")
    google_id: str | None = user_info.get("sub")
    google_name: str | None = user_info.get("name")

    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account does not have an email address",
        )

    # 1) Check for existing user by oauth_id
    existing_oauth_user = db.execute(
        select(User).where(User.oauth_provider == "google", User.oauth_id == google_id)
    ).scalar_one_or_none()

    if existing_oauth_user is not None:
        jwt_token = create_access_token(data={"sub": existing_oauth_user.email})
        return TokenResponse(access_token=jwt_token)

    # 2) Check for existing user by email (link account)
    existing_email_user = db.execute(
        select(User).where(User.email == google_email)
    ).scalar_one_or_none()

    if existing_email_user is not None:
        existing_email_user.oauth_provider = "google"
        existing_email_user.oauth_id = google_id
        db.commit()
        jwt_token = create_access_token(data={"sub": existing_email_user.email})
        return TokenResponse(access_token=jwt_token)

    # 3) Create new user
    new_user = User(
        email=google_email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        display_name=google_name,
        oauth_provider="google",
        oauth_id=google_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    jwt_token = create_access_token(data={"sub": new_user.email})
    return TokenResponse(access_token=jwt_token)
