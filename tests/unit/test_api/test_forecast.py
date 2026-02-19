"""Tests for the forecast endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app


@pytest.fixture
def mock_db():
    """Mock DB session."""
    return MagicMock()


@pytest.fixture
def forecast_app(mock_db):
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
def client(forecast_app):
    """Test HTTP client."""
    return TestClient(forecast_app)


class TestForecastGeocodeFailure:
    """When geocoding fails, return graceful error response."""

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_returns_unavailable_when_geocode_fails(self, mock_geocode, client):
        resp = client.post("/api/forecast", json={"address": "Unknown Place"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_version"] == "unavailable"
        assert data["predicted_value"] == 0.0
        assert data["address"] == "Unknown Place"

    @patch("pricepoint.api.routes.forecast._geocode_address", return_value=None)
    def test_response_has_all_fields(self, mock_geocode, client):
        resp = client.post("/api/forecast", json={"address": "Nowhere"})
        data = resp.json()
        assert "address" in data
        assert "predicted_value" in data
        assert "confidence_interval_low" in data
        assert "confidence_interval_high" in data
        assert "model_version" in data


class TestForecastModelUnavailable:
    """When the ML model is unavailable, return graceful error response."""

    @patch(
        "pricepoint.api.routes.forecast._load_model_and_predict",
        side_effect=Exception("MLflow unavailable"),
    )
    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame({"feat1": [1.0]}, index=[1]),
    )
    @patch(
        "pricepoint.api.routes.forecast._get_or_create_property_id",
        return_value=1,
    )
    @patch(
        "pricepoint.api.routes.forecast._geocode_address",
        return_value=(35.79, -78.78),
    )
    def test_returns_unavailable_when_model_fails(
        self, mock_geocode, mock_prop, mock_features, mock_predict, client
    ):
        resp = client.post("/api/forecast", json={"address": "123 Main St"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_version"] == "unavailable"
        assert data["predicted_value"] == 0.0


class TestForecastSuccess:
    """When everything works, return a real prediction."""

    @patch(
        "pricepoint.api.routes.forecast._load_model_and_predict",
        return_value=(350000.0, 315000.0, 385000.0, "run-abc123"),
    )
    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame({"feat1": [1.0]}, index=[1]),
    )
    @patch(
        "pricepoint.api.routes.forecast._get_or_create_property_id",
        return_value=1,
    )
    @patch(
        "pricepoint.api.routes.forecast._geocode_address",
        return_value=(35.79, -78.78),
    )
    def test_returns_prediction(self, mock_geocode, mock_prop, mock_features, mock_predict, client):
        resp = client.post(
            "/api/forecast",
            json={"address": "123 Main St", "city": "Raleigh", "state": "NC"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["predicted_value"] == 350000.0
        assert data["confidence_interval_low"] == 315000.0
        assert data["confidence_interval_high"] == 385000.0
        assert data["model_version"] == "run-abc123"
        assert data["address"] == "123 Main St"


class TestForecastCaching:
    """Test Valkey caching behavior."""

    @patch(
        "pricepoint.api.routes.forecast._geocode_address",
        return_value=(35.79, -78.78),
    )
    @patch(
        "pricepoint.api.routes.forecast._get_or_create_property_id",
        return_value=1,
    )
    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame({"feat1": [1.0]}, index=[1]),
    )
    @patch(
        "pricepoint.api.routes.forecast._load_model_and_predict",
        return_value=(300000.0, 270000.0, 330000.0, "run-cached"),
    )
    def test_caches_result_in_valkey(
        self,
        mock_predict,
        mock_features,
        mock_prop,
        mock_geocode,
        mock_db,
    ):
        """When valkey is available, results are cached."""
        app = create_app()

        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None

        def _override_get_db():
            yield mock_db

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        test_client = TestClient(app)
        resp = test_client.post("/api/forecast", json={"address": "456 Oak Ave"})
        assert resp.status_code == 200
        assert resp.json()["predicted_value"] == 300000.0

        # Verify valkey.set was called with 24h TTL
        mock_valkey.set.assert_called_once()
        call_args = mock_valkey.set.call_args
        assert call_args.kwargs.get("ex") == 86400 or call_args[1].get("ex") == 86400

        app.dependency_overrides.clear()

    def test_returns_cached_result(self, mock_db):
        """When valkey has a cached result, return it directly."""
        import json

        app = create_app()

        cached_data = {
            "address": "789 Pine Rd",
            "predicted_value": 250000.0,
            "confidence_interval_low": 225000.0,
            "confidence_interval_high": 275000.0,
            "model_version": "run-cached-v2",
        }
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = json.dumps(cached_data)

        def _override_get_db():
            yield mock_db

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        test_client = TestClient(app)
        resp = test_client.post("/api/forecast", json={"address": "789 Pine Rd"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["predicted_value"] == 250000.0
        assert data["model_version"] == "run-cached-v2"

        app.dependency_overrides.clear()
