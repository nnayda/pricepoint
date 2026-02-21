"""Tests for the data request endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pricepoint.db.models import DataRequest


class TestCreateDataRequest:
    def test_creates_request_returns_201(self, client, app):
        """POST /api/data-requests creates a new request."""
        mock_db = _get_mock_db(app)
        # No existing request
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # After commit + refresh, the model has these attrs
        new_req = _make_data_request(1, "123 Main St", "pending")
        mock_db.refresh.side_effect = lambda obj: _copy_attrs(new_req, obj)

        resp = client.post(
            "/api/data-requests",
            json={"address": "123 Main St", "lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["address"] == "123 Main St"
        assert data["status"] == "pending"
        assert "id" in data

    def test_deduplicates_pending_request(self, client, app):
        """POST /api/data-requests returns existing pending request."""
        mock_db = _get_mock_db(app)
        existing = _make_data_request(42, "123 Main St", "pending")
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing

        resp = client.post(
            "/api/data-requests",
            json={"address": "123 Main St", "lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == 42
        mock_db.add.assert_not_called()

    def test_accepts_optional_email(self, client, app):
        """POST /api/data-requests accepts optional email."""
        mock_db = _get_mock_db(app)
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        new_req = _make_data_request(2, "456 Oak Ave", "pending")
        mock_db.refresh.side_effect = lambda obj: _copy_attrs(new_req, obj)

        resp = client.post(
            "/api/data-requests",
            json={
                "address": "456 Oak Ave",
                "lat": 35.5,
                "lon": -78.5,
                "email": "user@example.com",
            },
        )
        assert resp.status_code == 201

    def test_missing_address_returns_422(self, client):
        """POST without address returns 422."""
        resp = client.post(
            "/api/data-requests",
            json={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        """POST without lat returns 422."""
        resp = client.post(
            "/api/data-requests",
            json={"address": "Test", "lon": -78.78},
        )
        assert resp.status_code == 422


class TestGetDataRequest:
    def test_returns_existing_request(self, client, app):
        """GET /api/data-requests/{id} returns the request."""
        mock_db = _get_mock_db(app)
        existing = _make_data_request(1, "123 Main St", "pending")
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing

        resp = client.get("/api/data-requests/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["address"] == "123 Main St"
        assert data["status"] == "pending"

    def test_returns_404_for_missing_request(self, client, app):
        """GET /api/data-requests/{id} returns 404 when not found."""
        mock_db = _get_mock_db(app)
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = client.get("/api/data-requests/999")
        assert resp.status_code == 404


# --- helpers ---


def _get_mock_db(app):
    """Extract the mock DB session from the app's dependency overrides."""
    from pricepoint.api.dependencies import get_db

    override = app.dependency_overrides[get_db]
    return next(override())


def _make_data_request(id_: int, address: str, status: str) -> MagicMock:
    obj = MagicMock(spec=DataRequest)
    obj.id = id_
    obj.address = address
    obj.status = status
    obj.created_at = datetime(2026, 2, 21, tzinfo=UTC)
    return obj


def _copy_attrs(source: MagicMock, target: DataRequest) -> None:
    """Simulate db.refresh by copying attrs from source mock to target model."""
    target.id = source.id
    target.address = source.address
    target.status = source.status
    target.created_at = source.created_at
