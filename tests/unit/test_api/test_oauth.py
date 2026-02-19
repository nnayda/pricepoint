"""Tests for Google OAuth authentication endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db
from pricepoint.api.main import create_app
from pricepoint.db.models import User


@pytest.fixture
def mock_db():
    """Return a mock DB session."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    return session


@pytest.fixture
def app(mock_db):
    """Create a test FastAPI application with mocked DB."""
    application = create_app()

    def _override_get_db():
        yield mock_db

    application.dependency_overrides[get_db] = _override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Return a TestClient for the app."""
    return TestClient(app)


def _make_user(
    user_id: int = 1,
    email: str = "oauth@example.com",
    display_name: str = "OAuth User",
    is_active: bool = True,
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
) -> MagicMock:
    """Build a mock User ORM object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.display_name = display_name
    user.is_active = is_active
    user.hashed_password = "hashed"
    user.oauth_provider = oauth_provider
    user.oauth_id = oauth_id
    user.created_at = None
    user.updated_at = None
    return user


# ---------- Settings ----------


def test_oauth_settings_defaults():
    """OAuth settings have correct defaults."""
    from pricepoint.config.settings import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.oauth_google_client_id == ""
    assert settings.oauth_google_client_secret == ""
    assert settings.oauth_redirect_uri == "http://localhost:5173/auth/google/callback"


# ---------- User model ----------


def test_user_model_has_oauth_fields():
    """User model exposes oauth_provider and oauth_id columns."""
    assert hasattr(User, "oauth_provider")
    assert hasattr(User, "oauth_id")


# ---------- GET /auth/google ----------


@patch("pricepoint.api.routes.auth.oauth")
def test_google_login_redirect(mock_oauth, client):
    """GET /auth/google redirects to Google's consent screen."""
    mock_google = MagicMock()
    redirect = RedirectResponse(url="https://accounts.google.com/o/oauth2/v2/auth?client_id=test")
    mock_google.authorize_redirect = AsyncMock(return_value=redirect)
    mock_oauth.google = mock_google

    # Use follow_redirects=False so TestClient doesn't follow the redirect
    resp = client.get("/api/auth/google", follow_redirects=False)
    assert resp.status_code == 307
    assert "accounts.google.com" in resp.headers["location"]
    mock_google.authorize_redirect.assert_awaited_once()


# ---------- GET /auth/google/callback ----------


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_creates_new_user(mock_oauth, client, mock_db):
    """Callback creates a new user when no matching user exists."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "google-123",
                "email": "new@example.com",
                "name": "New User",
            }
        }
    )
    mock_oauth.google = mock_google

    # No existing user found (default mock_db behaviour)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    def _refresh(user):
        user.id = 1
        user.email = "new@example.com"

    mock_db.refresh.side_effect = _refresh

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called()


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_links_existing_email_user(mock_oauth, client, mock_db):
    """Callback links Google account to existing user found by email."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "google-456",
                "email": "existing@example.com",
                "name": "Existing User",
            }
        }
    )
    mock_oauth.google = mock_google

    existing_user = _make_user(email="existing@example.com")

    # First call: search by oauth_id -> None; Second call: search by email -> user
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [None, existing_user]

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    # Should have linked the account
    assert existing_user.oauth_provider == "google"
    assert existing_user.oauth_id == "google-456"
    mock_db.commit.assert_called()
    # Should NOT have created a new user
    mock_db.add.assert_not_called()


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_logs_in_existing_oauth_user(mock_oauth, client, mock_db):
    """Callback logs in a user that already has a linked Google account."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "google-789",
                "email": "oauth@example.com",
                "name": "OAuth User",
            }
        }
    )
    mock_oauth.google = mock_google

    oauth_user = _make_user(
        email="oauth@example.com",
        oauth_provider="google",
        oauth_id="google-789",
    )
    # First call: search by oauth_id -> found
    mock_db.execute.return_value.scalar_one_or_none.return_value = oauth_user

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    # No new user created, no account linking
    mock_db.add.assert_not_called()


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_invalid_code(mock_oauth, client):
    """Callback with an invalid authorization code returns 401."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(side_effect=Exception("invalid_grant"))
    mock_oauth.google = mock_google

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 401
    assert "OAuth authentication failed" in resp.json()["detail"]


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_missing_email(mock_oauth, client):
    """Callback returns 400 when Google account has no email."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "google-no-email",
                "name": "No Email User",
            }
        }
    )
    mock_oauth.google = mock_google

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


@patch("pricepoint.api.routes.auth.oauth")
def test_google_callback_missing_userinfo(mock_oauth, client):
    """Callback returns 401 when token response has no userinfo."""
    mock_google = MagicMock()
    mock_google.authorize_access_token = AsyncMock(return_value={"access_token": "tok"})
    mock_oauth.google = mock_google

    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 401
    assert "user info" in resp.json()["detail"].lower()
