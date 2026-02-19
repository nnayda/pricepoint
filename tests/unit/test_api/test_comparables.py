"""Tests for the comparables endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app


@pytest.fixture
def mock_db():
    """Mock DB session."""
    return MagicMock()


@pytest.fixture
def comp_app(mock_db):
    """Create a test app with mocked dependencies."""
    application = create_app()

    def _override_get_db():
        yield mock_db

    async def _override_get_valkey():
        yield None

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_valkey] = _override_get_valkey
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(comp_app):
    """Test HTTP client."""
    return TestClient(comp_app)


def _make_listing(**overrides):
    """Create a mock RedfinListing with sensible defaults."""
    listing = MagicMock()
    listing.id = overrides.get("id", 1)
    listing.street_address = overrides.get("street_address", "100 Oak St")
    listing.city = overrides.get("city", "Cary")
    listing.state = overrides.get("state", "NC")
    listing.zip_code = overrides.get("zip_code", "27513")
    listing.sold_date = overrides.get("sold_date", datetime.now(tz=UTC) - timedelta(days=30))
    listing.sold_price = overrides.get("sold_price", 400000.0)
    listing.num_beds = overrides.get("num_beds", 4)
    listing.num_baths = overrides.get("num_baths", 3.0)
    listing.sqft = overrides.get("sqft", 2500)
    listing.price_per_sqft = overrides.get("price_per_sqft", 160.0)
    listing.location = MagicMock()
    return listing


class TestComparablesEmpty:
    """When no matching properties exist, return empty list."""

    def test_returns_empty_list_when_no_results(self, client, mock_db):
        """No comparable properties yields an empty list."""
        mock_db.execute.return_value.all.return_value = []
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestComparablesValidation:
    """Parameter validation."""

    def test_missing_required_params(self, client):
        """Missing lat/lon/beds/sqft returns 422."""
        resp = client.get("/api/comparables")
        assert resp.status_code == 422

    def test_missing_beds(self, client):
        """Missing beds returns 422."""
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "sqft": 2500},
        )
        assert resp.status_code == 422

    def test_missing_sqft(self, client):
        """Missing sqft returns 422."""
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "beds": 4},
        )
        assert resp.status_code == 422

    def test_invalid_lat_range(self, client):
        """lat outside [-90, 90] returns 422."""
        resp = client.get(
            "/api/comparables",
            params={"lat": 100.0, "lon": -78.78, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 422

    def test_invalid_lon_range(self, client):
        """lon outside [-180, 180] returns 422."""
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -200.0, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 422

    def test_sqft_must_be_positive(self, client):
        """sqft <= 0 returns 422."""
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "beds": 4, "sqft": 0},
        )
        assert resp.status_code == 422


class TestComparablesResults:
    """When comparable properties exist, return sorted results."""

    def test_returns_comparables_with_correct_schema(self, client, mock_db):
        """Response items have all expected fields."""
        listing = _make_listing()
        mock_db.execute.return_value.all.return_value = [(listing, 500.0)]

        # Mock the ST_Y/ST_X query for lat/lon extraction
        point_result = MagicMock()
        point_result.lat = 35.79
        point_result.lon = -78.78

        # First call returns comparables, second call returns lat/lon
        mock_db.execute.side_effect = [
            MagicMock(all=MagicMock(return_value=[(listing, 500.0)])),
            MagicMock(one=MagicMock(return_value=point_result)),
        ]

        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert "id" in item
        assert "address" in item
        assert "sale_price" in item
        assert "sold_date" in item
        assert "beds" in item
        assert "baths" in item
        assert "sqft" in item
        assert "price_per_sqft" in item
        assert "lat" in item
        assert "lon" in item

    def test_respects_limit_param(self, client, mock_db):
        """Only returns up to `limit` results."""
        listings = []
        for i in range(5):
            listings.append((_make_listing(id=i + 1), 500.0 + i * 100))

        point_result = MagicMock()
        point_result.lat = 35.79
        point_result.lon = -78.78

        side_effects = [MagicMock(all=MagicMock(return_value=listings))]
        # One point query per returned result (limited to 2)
        for _ in range(2):
            side_effects.append(MagicMock(one=MagicMock(return_value=point_result)))

        mock_db.execute.side_effect = side_effects

        resp = client.get(
            "/api/comparables",
            params={
                "lat": 35.79,
                "lon": -78.78,
                "beds": 4,
                "sqft": 2500,
                "limit": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_builds_full_address(self, client, mock_db):
        """Address includes street, city, state, zip."""
        listing = _make_listing(
            street_address="200 Pine St",
            city="Raleigh",
            state="NC",
            zip_code="27601",
        )
        point_result = MagicMock()
        point_result.lat = 35.78
        point_result.lon = -78.64

        mock_db.execute.side_effect = [
            MagicMock(all=MagicMock(return_value=[(listing, 1000.0)])),
            MagicMock(one=MagicMock(return_value=point_result)),
        ]

        resp = client.get(
            "/api/comparables",
            params={"lat": 35.78, "lon": -78.64, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["address"] == "200 Pine St, Raleigh, NC 27601"

    def test_uses_default_radius_and_limit(self, client, mock_db):
        """Defaults: radius_miles=3.0, limit=5."""
        mock_db.execute.return_value.all.return_value = []
        resp = client.get(
            "/api/comparables",
            params={"lat": 35.79, "lon": -78.78, "beds": 4, "sqft": 2500},
        )
        assert resp.status_code == 200
        # Just verify defaults work and return 200
        assert isinstance(resp.json(), list)
