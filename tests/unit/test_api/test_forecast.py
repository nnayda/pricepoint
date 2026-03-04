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

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_returns_stub_when_mlflow_unavailable(self, _mock_precomputed, client):
        """Falls back to stub importances when no model is available."""
        resp = client.get("/api/forecast/importance/1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 13  # 10 positive + 3 negative from stub

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_stub_response_has_correct_schema(self, _mock_precomputed, client):
        """Each attribution has feature, display_name, impact_dollars, group."""
        resp = client.get("/api/forecast/importance/1")
        data = resp.json()
        for item in data:
            assert "feature" in item
            assert "display_name" in item
            assert "impact_dollars" in item
            assert isinstance(item["impact_dollars"], float)
            assert "group" in item
            assert item["group"] in ("Property", "Location", "Economic", "Other")

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_stub_contains_positive_and_negative(self, _mock_precomputed, client):
        """Stub data includes both positive and negative impacts."""
        resp = client.get("/api/forecast/importance/1")
        data = resp.json()
        positives = [d for d in data if d["impact_dollars"] > 0]
        negatives = [d for d in data if d["impact_dollars"] < 0]
        assert len(positives) > 0
        assert len(negatives) > 0

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_display_names_match_mapping(self, _mock_precomputed, client):
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
    @patch("shap.TreeExplainer")
    @patch("pricepoint.models.inference.load_production_model")
    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_returns_shap_values_when_model_available(
        self, _mock_precomputed, mock_load, mock_tree_explainer, mock_features, client
    ):
        """When MLflow model is available, return per-instance SHAP values."""
        from pricepoint.models.inference import ModelInfo

        mock_model = MagicMock()
        mock_model.feature_names_in_ = np.array(["feat_a", "feat_b", "feat_c"])
        mock_load.return_value = ModelInfo(model=mock_model, version="1", run_id="run-1")

        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[25000.0, -8000.0, 3000.0]])
        mock_tree_explainer.return_value = mock_explainer

        resp = client.get("/api/forecast/importance/42")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        features = {d["feature"]: d["impact_dollars"] for d in data}
        assert features["feat_a"] == 25000.0
        assert features["feat_b"] == -8000.0
        assert features["feat_c"] == 3000.0

    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame(),
    )
    @patch("pricepoint.models.inference.load_production_model")
    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_falls_back_to_stub_when_features_empty(
        self, _mock_precomputed, mock_load, mock_features, client
    ):
        """When feature engineering returns empty DF, fall back to stub."""
        from pricepoint.models.inference import ModelInfo

        mock_load.return_value = ModelInfo(model=MagicMock(), version="1", run_id="run-1")

        resp = client.get("/api/forecast/importance/99")
        assert resp.status_code == 200
        data = resp.json()
        # Should be stub data (13 items)
        assert len(data) == 13

    def test_invalid_property_id_type(self, client):
        """Non-integer property_id returns 422."""
        resp = client.get("/api/forecast/importance/abc")
        assert resp.status_code == 422

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap")
    def test_returns_precomputed_when_available(self, mock_precomputed, client):
        """When precomputed SHAP exists, return it directly (no model load)."""
        from pricepoint.api.schemas.forecast import FeatureAttribution

        mock_precomputed.return_value = [
            FeatureAttribution(
                feature="sqft",
                display_name="Sqft",
                impact_dollars=25000.0,
                group="Property",
            ),
            FeatureAttribution(
                feature="crime_count_1km_1yr",
                display_name="Crime density (1km)",
                impact_dollars=-12000.0,
                group="Location",
            ),
        ]

        resp = client.get("/api/forecast/importance/42")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["feature"] == "sqft"
        assert data[0]["impact_dollars"] == 25000.0
        assert data[1]["feature"] == "crime_count_1km_1yr"

    @patch(
        "pricepoint.api.routes.forecast._build_features_for_property",
        return_value=pd.DataFrame(
            {"feat_a": [2.0], "feat_b": [3.0]},
            index=[42],
        ),
    )
    @patch("shap.TreeExplainer")
    @patch("pricepoint.models.inference.load_production_model")
    @patch("pricepoint.api.routes.forecast._load_precomputed_shap", return_value=None)
    def test_falls_back_to_ondemand_when_no_precomputed(
        self, mock_precomputed, mock_load, mock_tree_explainer, mock_features, client
    ):
        """When no precomputed SHAP, falls back to on-demand computation."""
        from pricepoint.models.inference import ModelInfo

        mock_model = MagicMock()
        mock_model.feature_names_in_ = np.array(["feat_a", "feat_b"])
        mock_load.return_value = ModelInfo(model=mock_model, version="1", run_id="run-1")

        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[15000.0, -6000.0]])
        mock_tree_explainer.return_value = mock_explainer

        resp = client.get("/api/forecast/importance/42")
        assert resp.status_code == 200
        data = resp.json()
        features = {d["feature"]: d["impact_dollars"] for d in data}
        assert features["feat_a"] == 15000.0
        assert features["feat_b"] == -6000.0

    @patch("pricepoint.api.routes.forecast._load_precomputed_shap")
    def test_precomputed_error_falls_through_to_stub(self, mock_precomputed, client):
        """When precomputed load raises and model unavailable, return stubs."""
        mock_precomputed.side_effect = Exception("DB error")

        resp = client.get("/api/forecast/importance/99")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 13  # Stub data


class TestShapListToAttributions:
    """Tests for _shap_list_to_attributions helper."""

    def test_filters_top_10_positive_and_negative(self):
        from pricepoint.api.routes.forecast import _shap_list_to_attributions

        shap_list = [
            {"feature": f"pos_{i}", "shap_value": float(1000 * (i + 1))} for i in range(15)
        ]
        shap_list += [
            {"feature": f"neg_{i}", "shap_value": float(-1000 * (i + 1))} for i in range(15)
        ]

        results = _shap_list_to_attributions(shap_list)

        positives = [r for r in results if r.impact_dollars > 0]
        negatives = [r for r in results if r.impact_dollars < 0]
        assert len(positives) == 10
        assert len(negatives) == 10

    def test_applies_display_names_and_groups(self):
        from pricepoint.api.routes.forecast import _shap_list_to_attributions

        shap_list = [
            {"feature": "dist_nearest_school_m", "shap_value": 5000.0},
            {"feature": "crime_count_1km_1yr", "shap_value": -3000.0},
        ]

        results = _shap_list_to_attributions(shap_list)

        by_feature = {r.feature: r for r in results}
        assert by_feature["dist_nearest_school_m"].display_name == "School proximity"
        assert by_feature["dist_nearest_school_m"].group == "Location"
        assert by_feature["crime_count_1km_1yr"].display_name == "Crime density (1km)"
        assert by_feature["crime_count_1km_1yr"].group == "Location"

    def test_rounds_impact_dollars(self):
        from pricepoint.api.routes.forecast import _shap_list_to_attributions

        shap_list = [{"feature": "sqft", "shap_value": 12345.6789}]
        results = _shap_list_to_attributions(shap_list)
        assert results[0].impact_dollars == 12345.68


class TestLoadPrecomputedShap:
    """Tests for _load_precomputed_shap."""

    def test_returns_none_when_no_record(self, mock_db):
        from pricepoint.api.routes.forecast import _load_precomputed_shap

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        result = _load_precomputed_shap(42, mock_db)
        assert result is None

    def test_returns_attributions_from_db(self, mock_db):
        from pricepoint.api.routes.forecast import _load_precomputed_shap

        record = MagicMock()
        record.shap_values = [
            {"feature": "sqft", "shap_value": 25000.0},
            {"feature": "bedrooms", "shap_value": -5000.0},
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            record
        )

        result = _load_precomputed_shap(42, mock_db)
        assert result is not None
        assert len(result) == 2
        assert result[0].feature == "sqft"
        assert result[0].impact_dollars == 25000.0
