"""Tests for API rate limiting."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db
from pricepoint.api.main import create_app
from pricepoint.api.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Reset the in-memory rate limiter state between tests."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def app():
    """Create a test FastAPI application with mocked DB."""
    application = create_app()

    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    def _override_get_db():
        yield mock_session

    application.dependency_overrides[get_db] = _override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return TestClient(app)


class TestRateLimitHeaders:
    """Rate limit headers are present in responses."""

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_forecast_endpoint_has_rate_limit_headers(self, mock_geocode, client):
        """Rate-limited endpoints include X-RateLimit-* headers."""
        resp = client.post("/api/forecast", json={"address": "123 Main St"})
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_rate_limit_header_values_are_valid(self, mock_geocode, client):
        """Rate limit headers contain valid integer values."""
        resp = client.post("/api/forecast", json={"address": "Addr 1"})
        limit = int(resp.headers["x-ratelimit-limit"])
        remaining = int(resp.headers["x-ratelimit-remaining"])
        reset = float(resp.headers["x-ratelimit-reset"])

        assert limit == 10  # forecast limit
        assert remaining >= 0
        assert reset > 0


class TestRateLimitExceeded:
    """Exceeding the rate limit returns 429."""

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_forecast_returns_429_when_exceeded(self, mock_geocode, client):
        """The forecast endpoint is limited to 10/minute; 11th request -> 429."""
        for i in range(10):
            resp = client.post("/api/forecast", json={"address": f"Addr {i}"})
            assert resp.status_code == 200, f"Request {i + 1} failed unexpectedly"

        # The 11th request should be rate limited
        resp = client.post("/api/forecast", json={"address": "One more"})
        assert resp.status_code == 429


class TestDifferentEndpointLimits:
    """Different endpoints have different rate limits."""

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_forecast_limit_is_lower_than_default(self, mock_geocode, client):
        """Forecast allows 10/minute while default allows 100/minute."""
        # Make 10 forecast requests (should all succeed)
        for i in range(10):
            resp = client.post("/api/forecast", json={"address": f"Addr {i}"})
            assert resp.status_code == 200

        # 11th forecast request should be rate limited
        resp = client.post("/api/forecast", json={"address": "Extra"})
        assert resp.status_code == 429

        # But a different endpoint (health) still works fine
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_auth_login_limit(self, client):
        """Auth login endpoint is limited to 5/minute."""
        for i in range(5):
            resp = client.post(
                "/api/auth/login",
                data={"username": f"user{i}@example.com", "password": "wrong"},
            )
            # 401 expected (invalid credentials), but not 429
            assert resp.status_code != 429, f"Request {i + 1} was rate-limited too early"

        # 6th request should be rate limited
        resp = client.post(
            "/api/auth/login",
            data={"username": "extra@example.com", "password": "wrong"},
        )
        assert resp.status_code == 429
