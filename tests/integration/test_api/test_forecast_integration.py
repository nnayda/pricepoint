"""Integration tests for the forecast endpoint."""


def test_forecast_stub_returns_valid_response(api_client):
    """POST /api/forecast with valid data should return 200 with expected fields."""
    response = api_client.post(
        "/api/forecast",
        json={"address": "100 Main St", "city": "Cary", "state": "NC"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "100 Main St"
    assert "predicted_value" in data
    assert "confidence_interval_low" in data
    assert "confidence_interval_high" in data
    assert "model_version" in data


def test_forecast_missing_address_returns_422(api_client):
    """POST /api/forecast without required address should return 422."""
    response = api_client.post("/api/forecast", json={"city": "Cary"})
    assert response.status_code == 422


def test_forecast_wrong_method_returns_405(api_client):
    """GET /api/forecast should return 405 Method Not Allowed."""
    response = api_client.get("/api/forecast")
    assert response.status_code == 405
