"""Tests for pricepoint.models.inference."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd


class TestLoadProductionModel:
    """Tests for load_production_model."""

    @patch("mlflow.sklearn.load_model")
    @patch("mlflow.tracking.MlflowClient")
    def test_returns_model_info_when_champion_exists(
        self,
        mock_client_cls: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "3"
        mock_version.run_id = "run-abc-123"
        mock_client.get_model_version_by_alias.return_value = mock_version
        mock_client_cls.return_value = mock_client

        sentinel_model = MagicMock()
        mock_load.return_value = sentinel_model

        from pricepoint.models.inference import ModelInfo, load_production_model

        result = load_production_model()

        assert isinstance(result, ModelInfo)
        assert result.model is sentinel_model
        assert result.version == "3"
        assert result.run_id == "run-abc-123"
        mock_client.get_model_version_by_alias.assert_called_once_with(
            "pricepoint-home-value", "champion"
        )
        mock_load.assert_called_once_with("models:/pricepoint-home-value@champion")

    @patch("mlflow.tracking.MlflowClient")
    def test_returns_none_when_no_champion_alias(
        self,
        mock_client_cls: MagicMock,
    ) -> None:
        import mlflow.exceptions

        mock_client = MagicMock()
        mock_client.get_model_version_by_alias.side_effect = mlflow.exceptions.MlflowException(
            "not found"
        )
        mock_client_cls.return_value = mock_client

        from pricepoint.models.inference import load_production_model

        result = load_production_model()
        assert result is None

    @patch("mlflow.sklearn.load_model")
    @patch("mlflow.tracking.MlflowClient")
    def test_custom_model_name(
        self,
        mock_client_cls: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "1"
        mock_version.run_id = "run-xyz"
        mock_client.get_model_version_by_alias.return_value = mock_version
        mock_client_cls.return_value = mock_client
        mock_load.return_value = MagicMock()

        from pricepoint.models.inference import load_production_model

        load_production_model(model_name="custom-model")
        mock_client.get_model_version_by_alias.assert_called_once_with("custom-model", "champion")

    @patch("mlflow.sklearn.load_model")
    @patch("mlflow.tracking.MlflowClient")
    def test_custom_alias(
        self,
        mock_client_cls: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.version = "2"
        mock_version.run_id = "run-456"
        mock_client.get_model_version_by_alias.return_value = mock_version
        mock_client_cls.return_value = mock_client
        mock_load.return_value = MagicMock()

        from pricepoint.models.inference import load_production_model

        load_production_model(alias="challenger")
        mock_client.get_model_version_by_alias.assert_called_once_with(
            "pricepoint-home-value", "challenger"
        )
        mock_load.assert_called_once_with("models:/pricepoint-home-value@challenger")


class TestPredictBatch:
    """Tests for predict_batch."""

    def test_returns_predictions_array(self) -> None:
        from pricepoint.models.inference import predict_batch

        model = MagicMock()
        model.predict.return_value = np.array([100000.0, 200000.0, 300000.0])

        features = pd.DataFrame(
            {"sqft": [1200, 1800, 2500], "bedrooms": [2, 3, 4]},
            index=[1, 2, 3],
        )

        result = predict_batch(model, features)

        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        np.testing.assert_array_equal(result, [100000.0, 200000.0, 300000.0])

    def test_drops_non_numeric_columns(self) -> None:
        from pricepoint.models.inference import predict_batch

        model = MagicMock()
        model.predict.return_value = np.array([150000.0])
        model.feature_names_in_ = None  # No feature alignment

        features = pd.DataFrame(
            {"sqft": [1500], "city": ["Raleigh"], "bedrooms": [3]},
            index=[1],
        )

        predict_batch(model, features)

        # Model should only receive numeric columns
        called_df = model.predict.call_args[0][0]
        assert "city" not in called_df.columns
        assert "sqft" in called_df.columns
        assert "bedrooms" in called_df.columns

    def test_aligns_columns_to_model_features(self) -> None:
        from pricepoint.models.inference import predict_batch

        model = MagicMock()
        model.predict.return_value = np.array([200000.0])
        model.feature_names_in_ = np.array(["sqft", "bedrooms", "lot_size"])

        features = pd.DataFrame(
            {"sqft": [1500], "bedrooms": [3], "extra_col": [42]},
            index=[1],
        )

        predict_batch(model, features)

        called_df = model.predict.call_args[0][0]
        assert list(called_df.columns) == ["sqft", "bedrooms", "lot_size"]
        assert "extra_col" not in called_df.columns
        # Missing column should be filled with NaN
        assert np.isnan(called_df["lot_size"].iloc[0])


class TestGetModelMetrics:
    """Tests for get_model_metrics."""

    @patch("mlflow.tracking.MlflowClient")
    def test_returns_metrics_dict(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_run = MagicMock()
        mock_run.data.metrics = {"mae": 15000.0, "rmse": 22000.0, "mape": 8.5, "r2": 0.87}
        mock_client.get_run.return_value = mock_run
        mock_client_cls.return_value = mock_client

        from pricepoint.models.inference import get_model_metrics

        result = get_model_metrics("run-abc-123")

        assert result == {"mae": 15000.0, "rmse": 22000.0, "mape": 8.5, "r2": 0.87}
        mock_client.get_run.assert_called_once_with("run-abc-123")

    @patch("mlflow.tracking.MlflowClient")
    def test_returns_empty_dict_when_no_metrics(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_run = MagicMock()
        mock_run.data.metrics = {}
        mock_client.get_run.return_value = mock_run
        mock_client_cls.return_value = mock_client

        from pricepoint.models.inference import get_model_metrics

        result = get_model_metrics("run-empty")
        assert result == {}


class TestComputeConfidenceInterval:
    """Tests for compute_confidence_interval."""

    def test_uses_mape_when_available(self) -> None:
        from pricepoint.models.inference import compute_confidence_interval

        low, high = compute_confidence_interval(400000.0, {"mape": 10.0, "rmse": 50000.0})

        # margin = 400000 * 10/100 = 40000
        assert low == 360000.0
        assert high == 440000.0

    def test_falls_back_to_rmse(self) -> None:
        from pricepoint.models.inference import compute_confidence_interval

        low, high = compute_confidence_interval(300000.0, {"rmse": 25000.0, "mae": 18000.0})

        assert low == 275000.0
        assert high == 325000.0

    def test_falls_back_to_ten_percent(self) -> None:
        from pricepoint.models.inference import compute_confidence_interval

        low, high = compute_confidence_interval(500000.0, {})

        # margin = 500000 * 0.10 = 50000
        assert low == 450000.0
        assert high == 550000.0

    def test_ten_percent_fallback_with_irrelevant_metrics(self) -> None:
        from pricepoint.models.inference import compute_confidence_interval

        low, high = compute_confidence_interval(200000.0, {"r2": 0.9, "mae": 12000.0})

        # Neither mape nor rmse present → 10%
        assert low == 180000.0
        assert high == 220000.0


class TestScoreAllProperties:
    """Tests for score_all_properties."""

    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_no_model(
        self,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = None
        db = MagicMock()

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0
        db.execute.assert_not_called()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.get_model_metrics")
    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_no_properties(
        self,
        mock_load: MagicMock,
        mock_metrics: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        from pricepoint.models.inference import ModelInfo

        mock_load.return_value = ModelInfo(model=MagicMock(), version="1", run_id="run-1")
        mock_metrics.return_value = {}
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0
        mock_assemble.assert_not_called()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.get_model_metrics")
    @patch("pricepoint.models.inference.load_production_model")
    def test_scores_properties_and_commits(
        self,
        mock_load: MagicMock,
        mock_metrics: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        from pricepoint.models.inference import ModelInfo

        model = MagicMock()
        model.predict.return_value = np.array([250000.0, 350000.0])
        mock_load.return_value = ModelInfo(model=model, version="5", run_id="run-abc")
        mock_metrics.return_value = {"mape": 8.0}

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(1,), (2,)]

        # No existing valuations
        db.query.return_value.filter.return_value.first.return_value = None

        features = pd.DataFrame(
            {"sqft": [1500, 2200], "bedrooms": [3, 4]},
            index=pd.Index([1, 2], name="property_id"),
        )
        mock_assemble.return_value = features

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)

        assert result == 2
        assert db.add.call_count == 2
        db.commit.assert_called_once()

        # Verify first valuation has correct fields
        first_val = db.add.call_args_list[0][0][0]
        assert first_val.value == 250000.0
        assert first_val.model_version == "5"
        assert first_val.confidence_low == 230000.0  # 250000 - 250000*0.08
        assert first_val.confidence_high == 270000.0  # 250000 + 250000*0.08

        second_val = db.add.call_args_list[1][0][0]
        assert second_val.value == 350000.0
        assert second_val.model_version == "5"
        assert second_val.confidence_low == 322000.0  # 350000 - 350000*0.08
        assert second_val.confidence_high == 378000.0  # 350000 + 350000*0.08

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.get_model_metrics")
    @patch("pricepoint.models.inference.load_production_model")
    def test_updates_existing_valuations(
        self,
        mock_load: MagicMock,
        mock_metrics: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        from pricepoint.models.inference import ModelInfo

        model = MagicMock()
        model.predict.return_value = np.array([300000.0])
        mock_load.return_value = ModelInfo(model=model, version="7", run_id="run-xyz")
        mock_metrics.return_value = {"mape": 10.0}

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(5,)]

        existing_val = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing_val

        features = pd.DataFrame(
            {"sqft": [2000]},
            index=pd.Index([5], name="property_id"),
        )
        mock_assemble.return_value = features

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)

        assert result == 1
        assert existing_val.value == 300000.0
        assert existing_val.model_version == "7"
        assert existing_val.confidence_low == 270000.0  # 300000 - 300000*0.10
        assert existing_val.confidence_high == 330000.0  # 300000 + 300000*0.10
        db.add.assert_not_called()
        db.commit.assert_called_once()

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.get_model_metrics")
    @patch("pricepoint.models.inference.load_production_model")
    def test_returns_zero_when_features_empty(
        self,
        mock_load: MagicMock,
        mock_metrics: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        from pricepoint.models.inference import ModelInfo

        mock_load.return_value = ModelInfo(model=MagicMock(), version="1", run_id="run-1")
        mock_metrics.return_value = {}
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(1,)]
        mock_assemble.return_value = pd.DataFrame()

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)
        assert result == 0

    @patch("pricepoint.models.inference.assemble_features")
    @patch("pricepoint.models.inference.get_model_metrics")
    @patch("pricepoint.models.inference.load_production_model")
    def test_handles_metrics_fetch_failure(
        self,
        mock_load: MagicMock,
        mock_metrics: MagicMock,
        mock_assemble: MagicMock,
    ) -> None:
        """When get_model_metrics raises, scoring continues with 10% fallback."""
        from pricepoint.models.inference import ModelInfo

        model = MagicMock()
        model.predict.return_value = np.array([200000.0])
        mock_load.return_value = ModelInfo(model=model, version="2", run_id="run-fail")
        mock_metrics.side_effect = Exception("MLflow unreachable")

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [(10,)]
        db.query.return_value.filter.return_value.first.return_value = None

        features = pd.DataFrame(
            {"sqft": [1800]},
            index=pd.Index([10], name="property_id"),
        )
        mock_assemble.return_value = features

        from pricepoint.models.inference import score_all_properties

        result = score_all_properties(db)

        assert result == 1
        val = db.add.call_args_list[0][0][0]
        assert val.model_version == "2"
        # 10% fallback: 200000 * 0.10 = 20000
        assert val.confidence_low == 180000.0
        assert val.confidence_high == 220000.0


class TestComputeShapValues:
    """Tests for compute_shap_values."""

    @patch("pricepoint.models.inference.shap")
    def test_returns_sorted_shap_values(self, mock_shap: MagicMock) -> None:
        from pricepoint.models.inference import compute_shap_values

        model = MagicMock()
        model.feature_names_in_ = np.array(["sqft", "bedrooms", "lot_size"])

        features = pd.DataFrame(
            {"sqft": [1500.0], "bedrooms": [3.0], "lot_size": [0.25]},
            index=[1],
        )

        # Mock TreeExplainer to return known SHAP values
        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[25000.0, -5000.0, 8000.0]])
        mock_shap.TreeExplainer.return_value = mock_explainer

        result = compute_shap_values(model, features)

        assert len(result) == 3
        # Sorted by absolute value descending
        assert result[0]["feature"] == "sqft"
        assert result[0]["shap_value"] == 25000.0
        assert result[1]["feature"] == "lot_size"
        assert result[1]["shap_value"] == 8000.0
        assert result[2]["feature"] == "bedrooms"
        assert result[2]["shap_value"] == -5000.0

    @patch("pricepoint.models.inference.shap")
    def test_aligns_columns_to_model_features(self, mock_shap: MagicMock) -> None:
        from pricepoint.models.inference import compute_shap_values

        model = MagicMock()
        model.feature_names_in_ = np.array(["sqft", "lot_size"])

        # features has extra column "bedrooms" not in model
        features = pd.DataFrame(
            {"sqft": [1500.0], "bedrooms": [3.0], "lot_size": [0.25]},
            index=[1],
        )

        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[20000.0, 5000.0]])
        mock_shap.TreeExplainer.return_value = mock_explainer

        result = compute_shap_values(model, features)

        assert len(result) == 2
        features_returned = {r["feature"] for r in result}
        assert features_returned == {"sqft", "lot_size"}

    @patch("pricepoint.models.inference.shap")
    def test_handles_model_without_feature_names(self, mock_shap: MagicMock) -> None:
        from pricepoint.models.inference import compute_shap_values

        model = MagicMock(spec=[])  # No feature_names_in_ attribute

        features = pd.DataFrame(
            {"sqft": [1500.0], "bedrooms": [3.0]},
            index=[1],
        )

        mock_explainer = MagicMock()
        mock_explainer.shap_values.return_value = np.array([[10000.0, -3000.0]])
        mock_shap.TreeExplainer.return_value = mock_explainer

        result = compute_shap_values(model, features)

        assert len(result) == 2
        assert result[0]["feature"] == "sqft"
        assert result[0]["shap_value"] == 10000.0
        assert result[1]["feature"] == "bedrooms"
        assert result[1]["shap_value"] == -3000.0
