"""Tests for health check endpoints."""

from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError


def test_health_endpoint(client):
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint(client):
    """GET /ready should return 200 with status ready when DB is reachable."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_endpoint_db_unreachable(app):
    """GET /ready should return 503 when the database is unreachable."""
    from fastapi.testclient import TestClient

    from pricepoint.api.dependencies import get_db

    def _broken_db():
        mock_session = MagicMock()
        mock_session.execute.side_effect = OperationalError("connection refused", {}, None)
        yield mock_session

    app.dependency_overrides[get_db] = _broken_db
    broken_client = TestClient(app)

    response = broken_client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_metrics_endpoint(client):
    """GET /metrics should return prometheus-format metrics data."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    # Prometheus metrics contain HELP and TYPE annotations
    body = response.text
    assert "# HELP" in body
    assert "# TYPE" in body


def test_stats_endpoint(app):
    """GET /api/stats should return listing count, photos analyzed, and data source count."""
    from fastapi.testclient import TestClient

    from pricepoint.api.dependencies import get_db

    mock_session = MagicMock()
    # Two calls to execute().scalar(): listing_count then photos_analyzed
    mock_session.execute.return_value.scalar.side_effect = [42, 150]

    def _mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_db

    # Clear the stats cache so the endpoint queries the DB
    import pricepoint.api.routes.health as health_mod

    health_mod._stats_cache["ts"] = 0.0
    health_mod._stats_cache.pop("listing_count", None)

    test_client = TestClient(app)
    response = test_client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data == {"listing_count": 42, "photos_analyzed": 150, "data_source_count": 8}


def test_stats_endpoint_uses_cache(app):
    """GET /api/stats should use cached values within TTL."""
    import time

    from fastapi.testclient import TestClient

    import pricepoint.api.routes.health as health_mod

    health_mod._stats_cache["listing_count"] = 99
    health_mod._stats_cache["photos_analyzed"] = 500
    health_mod._stats_cache["data_source_count"] = 8
    health_mod._stats_cache["ts"] = time.monotonic()

    test_client = TestClient(app)
    response = test_client.get("/api/stats")
    assert response.status_code == 200
    assert response.json() == {"listing_count": 99, "photos_analyzed": 500, "data_source_count": 8}


def test_forecast_endpoint_stub(client):
    """POST /api/forecast should return a stub response."""
    response = client.post(
        "/api/forecast",
        json={"address": "123 Main St", "city": "Test City", "state": "PA"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "123 Main St"
    assert data["model_version"] == "unavailable"
    assert "predicted_value" in data
