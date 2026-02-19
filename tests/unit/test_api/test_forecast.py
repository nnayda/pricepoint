"""Tests for the forecast endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app
from pricepoint.api.routes.forecast import FEATURE_DISPLAY_NAMES


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


class TestFeatureImportance:
    """Tests for GET /api/forecast/importance/{property_id}."""

    def test_returns_stub_when_mlflow_unavailable(self, client):
        """Falls back to stub importances when no model is available."""
        resp = client.get("/api/forecast/importance/1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 15  # 10 positive + 5 negative from stub

    def test_stub_response_has_correct_schema(self, client):
        """Each attribution has feature, display_name, impact_dollars."""
        resp = client.get("/api/forecast/importance/1")
        data = resp.json()
        for item in data:
            assert "feature" in item
            assert "display_name" in item
            assert "impact_dollars" in item
            assert isinstance(item["impact_dollars"], float)

    def test_stub_contains_positive_and_negative(self, client):
        """Stub data includes both positive and negative impacts."""
        resp = client.get("/api/forecast/importance/1")
        data = resp.json()
        positives = [d for d in data if d["impact_dollars"] > 0]
        negatives = [d for d in data if d["impact_dollars"] < 0]
        assert len(positives) > 0
        assert len(negatives) > 0

    def test_display_names_match_mapping(self, client):
        """Display names should come from FEATURE_DISPLAY_NAMES."""
        resp = client.get("/api/forecast/importance/1")
        data = resp.json()
        for item in data:
            if item["feature"] in FEATURE_DISPLAY_NAMES:
                assert item["display_name"] == FEATURE_DISPLAY_NAMES[item["feature"]]

    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame(
            {"feat_a": [2.0], "feat_b": [3.0], "feat_c": [1.0]},
            index=[42],
        ),
    )
    @patch("mlflow.pyfunc.load_model")
    def test_returns_model_importances_when_available(self, mock_load_model, mock_features, client):
        """When MLflow model has feature_importances_, use them."""
        mock_model = MagicMock()
        mock_model._model_impl.feature_importances_ = np.array([0.5, -0.3, 0.1])
        mock_load_model.return_value = mock_model

        resp = client.get("/api/forecast/importance/42")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # feat_a: 0.5 * 2.0 = 1.0 (positive)
        # feat_b: -0.3 * 3.0 = -0.9 (negative)
        # feat_c: 0.1 * 1.0 = 0.1 (positive)
        features = {d["feature"]: d["impact_dollars"] for d in data}
        assert features["feat_a"] == 1.0
        assert features["feat_b"] == -0.9
        assert features["feat_c"] == 0.1

    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame(),
    )
    @patch("mlflow.pyfunc.load_model")
    def test_falls_back_to_stub_when_features_empty(self, mock_load_model, mock_features, client):
        """When feature engineering returns empty DF, fall back to stub."""
        mock_model = MagicMock()
        mock_model._model_impl.feature_importances_ = np.array([0.5])
        mock_load_model.return_value = mock_model

        resp = client.get("/api/forecast/importance/99")
        assert resp.status_code == 200
        data = resp.json()
        # Should be stub data (15 items)
        assert len(data) == 15

    def test_invalid_property_id_type(self, client):
        """Non-integer property_id returns 422."""
        resp = client.get("/api/forecast/importance/abc")
        assert resp.status_code == 422
