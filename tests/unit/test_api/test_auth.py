"""Tests for authentication endpoints: register, login, profile."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.auth import get_current_user, hash_password, verify_password
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
    email: str = "test@example.com",
    display_name: str = "Test User",
    is_active: bool = True,
) -> MagicMock:
    """Build a mock User ORM object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.display_name = display_name
    user.is_active = is_active
    user.hashed_password = hash_password("secret123")
    user.created_at = None
    user.updated_at = None
    return user


# ---------- password utilities ----------


def test_hash_and_verify_password():
    """hash_password + verify_password round-trips correctly."""
    hashed = hash_password("my-password")
    assert verify_password("my-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


# ---------- POST /auth/register ----------


def test_register_success(client, mock_db):
    """Registering a new user returns 201 with user data."""
    # No existing user
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    # After add+commit+refresh, simulate returning user
    def _refresh(user):
        user.id = 1
        user.is_active = True
        user.created_at = None

    mock_db.refresh.side_effect = _refresh

    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "secret123", "display_name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["display_name"] == "New User"
    assert "hashed_password" not in data
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_register_duplicate_email(client, mock_db):
    """Registering with an existing email returns 409."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()

    resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


def test_register_invalid_email(client):
    """Registering with an invalid email returns 422."""
    resp = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "secret123"},
    )
    assert resp.status_code == 422


# ---------- POST /auth/login ----------


def test_login_success(client, mock_db):
    """Valid credentials return a JWT token."""
    user = _make_user()
    mock_db.execute.return_value.scalar_one_or_none.return_value = user

    resp = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, mock_db):
    """Wrong password returns 401."""
    user = _make_user()
    mock_db.execute.return_value.scalar_one_or_none.return_value = user

    resp = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client, mock_db):
    """Logging in with an unknown email returns 401."""
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    resp = client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


# ---------- GET /auth/me ----------


def test_get_me_success(client, app):
    """Authenticated user can fetch their own profile."""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"


def test_get_me_no_token(client):
    """Accessing /auth/me without a token returns 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_get_me_invalid_token(client):
    """Accessing /auth/me with a bad token returns 401."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


# ---------- PUT /auth/me ----------


def test_update_me_success(client, app, mock_db):
    """Authenticated user can update their display name."""
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    def _refresh(obj):
        obj.display_name = "Updated Name"

    mock_db.refresh.side_effect = _refresh

    resp = client.put("/api/auth/me", json={"display_name": "Updated Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Updated Name"
    mock_db.commit.assert_called()


def test_update_me_no_token(client):
    """Updating profile without auth returns 401."""
    resp = client.put("/api/auth/me", json={"display_name": "Hacker"})
    assert resp.status_code == 401


# ---------- get_current_user dependency ----------


def test_get_current_user_inactive(client, mock_db):
    """An inactive user's token should be rejected with 401."""
    from pricepoint.api.auth import create_access_token

    token = create_access_token(data={"sub": "inactive@example.com"})
    inactive_user = _make_user(email="inactive@example.com", is_active=False)
    mock_db.execute.return_value.scalar_one_or_none.return_value = inactive_user

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
