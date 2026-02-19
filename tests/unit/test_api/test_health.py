"""Tests for health check endpoints."""


def test_health_endpoint(client):
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint(client):
    """GET /ready should return 200 with status ready."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


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
