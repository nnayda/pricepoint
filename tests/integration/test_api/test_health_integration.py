"""Integration tests for health endpoints with a real database."""


def test_health_returns_ok(api_client):
    """GET /health should return 200."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_returns_ready(api_client):
    """GET /ready should return 200."""
    response = api_client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
