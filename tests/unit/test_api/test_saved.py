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
    listing.city = "Cary"
    listing.state = "NC"
    listing.zip_code = "27513"
    listing.listing_status = "Sold"
    listing.listing_price = 350000.0
    listing.sold_price = 345000.0
    listing.num_beds = 3
    listing.num_baths = 2.5
    listing.sqft = 1800
    listing.year_built = 2005
    listing.property_photos = ["photos/abc123.jpg", "photos/def456.jpg"]
    listing.location = MagicMock()  # non-None to trigger coord query
    return listing


def _make_enriched_row(sp: MagicMock) -> MagicMock:
    """Build a mock row returned by the enriched list query."""
    row = MagicMock()
    # Index access: row[0] returns the SavedProperty
    row.__getitem__ = lambda self, idx: sp if idx == 0 else None
    row.street_address = "123 Main St"
    row.city = "Cary"
    row.state = "NC"
    row.zip_code = "27513"
    row.listing_status = "Sold"
    row.listing_price = 350000.0
    row.sold_price = 345000.0
    row.num_beds = 3
    row.num_baths = 2.5
    row.sqft = 1800
    row.year_built = 2005
    row.property_photos = ["photos/abc123.jpg", "photos/def456.jpg"]
    row.lat = 35.79
    row.lon = -78.78
    return row


def _make_enriched_row_no_photos(sp: MagicMock) -> MagicMock:
    """Build a mock row with no photos."""
    row = _make_enriched_row(sp)
    row.property_photos = None
    return row


class TestListSaved:
    """GET /api/saved"""

    def test_list_empty(self, client, mock_db):
        mock_db.execute.return_value.all.return_value = []
        resp = client.get("/api/saved")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_saved_properties(self, client, mock_db):
        sp = _make_saved_property()
        row = _make_enriched_row(sp)
        mock_db.execute.return_value.all.return_value = [row]
        resp = client.get("/api/saved")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["listing_id"] == 10
        assert data[0]["listing_address"] == "123 Main St"
        assert data[0]["city"] == "Cary"
        assert data[0]["state"] == "NC"
        assert data[0]["zip_code"] == "27513"
        assert data[0]["listing_status"] == "Sold"
        assert data[0]["listing_price"] == 350000.0
        assert data[0]["sold_price"] == 345000.0
        assert data[0]["num_beds"] == 3
        assert data[0]["num_baths"] == 2.5
        assert data[0]["sqft"] == 1800
        assert data[0]["year_built"] == 2005
        assert data[0]["lat"] == 35.79
        assert data[0]["lon"] == -78.78

    def test_list_photo_url_construction(self, client, mock_db):
        sp = _make_saved_property()
        row = _make_enriched_row(sp)
        mock_db.execute.return_value.all.return_value = [row]
        resp = client.get("/api/saved")
        data = resp.json()
        assert data[0]["photo_url"] == "/api/photos/photos/abc123.jpg"

    def test_list_null_photos(self, client, mock_db):
        sp = _make_saved_property()
        row = _make_enriched_row_no_photos(sp)
        mock_db.execute.return_value.all.return_value = [row]
        resp = client.get("/api/saved")
        data = resp.json()
        assert data[0]["photo_url"] is None


class TestSaveProperty:
    """POST /api/saved"""

    def test_save_success(self, client, mock_db):
        listing = _make_listing()
        # First execute: listing lookup
        # Second execute: duplicate check
        # Third execute: coord query (location is non-None)
        coord_row = MagicMock()
        coord_row.lat = 35.79
        coord_row.lon = -78.78
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [listing, None]
        mock_db.execute.return_value.one.return_value = coord_row

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
        assert data["city"] == "Cary"
        assert data["num_beds"] == 3
        assert data["photo_url"] == "/api/photos/photos/abc123.jpg"
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

        # First call: lookup saved property; second call: enriched listing row
        enriched_row = MagicMock()
        enriched_row.street_address = "123 Main St"
        enriched_row.city = "Cary"
        enriched_row.state = "NC"
        enriched_row.zip_code = "27513"
        enriched_row.listing_status = "Sold"
        enriched_row.listing_price = 350000.0
        enriched_row.sold_price = 345000.0
        enriched_row.num_beds = 3
        enriched_row.num_baths = 2.5
        enriched_row.sqft = 1800
        enriched_row.year_built = 2005
        enriched_row.property_photos = ["photos/abc123.jpg"]
        enriched_row.lat = 35.79
        enriched_row.lon = -78.78

        mock_db.execute.return_value.scalar_one_or_none.return_value = sp
        mock_db.execute.return_value.one_or_none.return_value = enriched_row

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
