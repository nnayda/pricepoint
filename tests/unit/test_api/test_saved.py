"""Tests for saved-property endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.auth import get_current_user
from pricepoint.api.dependencies import get_db
from pricepoint.api.main import create_app
from pricepoint.db.models import RedfinListing, SavedProperty, User


@pytest.fixture
def fake_user():
    """Return a mock User representing the authenticated caller."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def other_user():
    """Return a mock User representing a different user."""
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "other@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    """Return a mock database session."""
    return MagicMock()


@pytest.fixture
def client(fake_user, mock_db):
    """Create a test client with mocked auth and DB."""
    app = create_app()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _make_saved_property(
    id: int = 1,
    user_id: int = 1,
    listing_id: int = 10,
    notes: str | None = None,
) -> MagicMock:
    sp = MagicMock(spec=SavedProperty)
    sp.id = id
    sp.user_id = user_id
    sp.listing_id = listing_id
    sp.notes = notes
    sp.created_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return sp


def _make_listing(id: int = 10, street_address: str = "123 Main St") -> MagicMock:
    listing = MagicMock(spec=RedfinListing)
    listing.id = id
    listing.street_address = street_address
    return listing


class TestListSaved:
    """GET /api/saved"""

    def test_list_empty(self, client, mock_db):
        mock_db.execute.return_value.all.return_value = []
        resp = client.get("/api/saved")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_saved_properties(self, client, mock_db):
        sp = _make_saved_property()
        mock_db.execute.return_value.all.return_value = [(sp, "123 Main St")]
        resp = client.get("/api/saved")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["listing_id"] == 10
        assert data[0]["listing_address"] == "123 Main St"


class TestSaveProperty:
    """POST /api/saved"""

    def test_save_success(self, client, mock_db):
        listing = _make_listing()
        # First execute: listing lookup
        # Second execute: duplicate check
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [listing, None]

        # After commit + refresh, the saved object needs to have attributes
        def _refresh(obj):
            obj.id = 1
            obj.created_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)

        mock_db.refresh.side_effect = _refresh

        resp = client.post("/api/saved", json={"listing_id": 10, "notes": "Great house"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["listing_id"] == 10
        assert data["notes"] == "Great house"
        assert data["listing_address"] == "123 Main St"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_save_listing_not_found(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        resp = client.post("/api/saved", json={"listing_id": 999})
        assert resp.status_code == 404
        assert "Listing not found" in resp.json()["detail"]

    def test_save_duplicate(self, client, mock_db):
        listing = _make_listing()
        existing = _make_saved_property()
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [listing, existing]
        resp = client.post("/api/saved", json={"listing_id": 10})
        assert resp.status_code == 409
        assert "already saved" in resp.json()["detail"]


class TestUpdateSaved:
    """PUT /api/saved/{id}"""

    def test_update_notes(self, client, mock_db):
        sp = _make_saved_property(notes="old")
        listing = _make_listing()

        # First call: lookup saved property; second call: lookup listing for address
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [sp, listing]

        def _refresh(obj):
            pass  # notes already updated in-place

        mock_db.refresh.side_effect = _refresh

        resp = client.put("/api/saved/1", json={"notes": "updated notes"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes"] == "updated notes"

    def test_update_not_found(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        resp = client.put("/api/saved/999", json={"notes": "x"})
        assert resp.status_code == 404

    def test_update_forbidden(self, client, mock_db):
        sp = _make_saved_property(user_id=99)  # different owner
        mock_db.execute.return_value.scalar_one_or_none.return_value = sp
        resp = client.put("/api/saved/1", json={"notes": "x"})
        assert resp.status_code == 403


class TestDeleteSaved:
    """DELETE /api/saved/{id}"""

    def test_delete_success(self, client, mock_db):
        sp = _make_saved_property()
        mock_db.execute.return_value.scalar_one_or_none.return_value = sp
        resp = client.delete("/api/saved/1")
        assert resp.status_code == 204
        mock_db.delete.assert_called_once_with(sp)
        mock_db.commit.assert_called_once()

    def test_delete_not_found(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        resp = client.delete("/api/saved/999")
        assert resp.status_code == 404

    def test_delete_forbidden(self, client, mock_db):
        sp = _make_saved_property(user_id=99)
        mock_db.execute.return_value.scalar_one_or_none.return_value = sp
        resp = client.delete("/api/saved/1")
        assert resp.status_code == 403
        mock_db.delete.assert_not_called()
