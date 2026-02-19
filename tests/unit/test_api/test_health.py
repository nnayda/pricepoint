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
