"""Tests for pricepoint.models.evaluation."""

import numpy as np
import pandas as pd
import pytest

from pricepoint.models.evaluation import evaluate_model
from pricepoint.models.training import train_model


@pytest.fixture()
def trained_model_and_data(synthetic_df: pd.DataFrame):
    """Train a model and return it along with test data."""
    model, _test_indices = train_model(features=synthetic_df, log_transform_target=False)
    # Use full df as test data for deterministic evaluation
    return model, synthetic_df


class TestEvaluateModel:
    """Tests for evaluate_model."""

    def test_returns_expected_keys(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "mape" in metrics
        assert "r2" in metrics
        assert "median_ae" in metrics

    def test_metrics_are_numeric(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        for key in ("mae", "rmse", "mape", "r2", "median_ae"):
            assert isinstance(metrics[key], float)

    def test_feature_importance_included(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        assert "feature_importance_top20" in metrics
        assert isinstance(metrics["feature_importance_top20"], dict)
        assert len(metrics["feature_importance_top20"]) > 0

    def test_r2_is_reasonable(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        # On training data, R² should be high
        assert metrics["r2"] > 0.9

    def test_prediction_arrays_included(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        assert "_y_true" in metrics
        assert "_y_pred" in metrics
        assert "_x_test" in metrics
        assert isinstance(metrics["_y_true"], np.ndarray)
        assert isinstance(metrics["_y_pred"], np.ndarray)
        assert isinstance(metrics["_x_test"], pd.DataFrame)
        assert len(metrics["_y_true"]) == len(metrics["_y_pred"])

    def test_missing_target_raises(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        with pytest.raises(ValueError, match="Target column"):
            evaluate_model(model=model, test_features=df, target_col="nonexistent")

    def test_log_target_inverse_transform(self, synthetic_df: pd.DataFrame) -> None:
        """When model has log_target=True, evaluate should inverse-transform."""
        model, _ = train_model(features=synthetic_df, log_transform_target=True)
        metrics = evaluate_model(model=model, test_features=synthetic_df, segment_col=None)
        # Metrics should be in dollar-space (positive values)
        assert metrics["mae"] > 0
        assert metrics["rmse"] > 0
        # Predictions should be in dollar-space
        assert metrics["_y_true"].mean() > 1000

    def test_segment_metrics(self, synthetic_df: pd.DataFrame) -> None:
        """When segment column exists, segment metrics should be computed."""
        df = synthetic_df.copy()
        df["census_tract_geoid"] = ["tract_A"] * 100 + ["tract_B"] * 100
        model, _ = train_model(features=df, log_transform_target=False)
        metrics = evaluate_model(model=model, test_features=df, segment_col="census_tract_geoid")
        assert "segment_metrics" in metrics
        seg = metrics["segment_metrics"]
        assert isinstance(seg, dict)
        for tract_metrics in seg.values():
            assert "mae" in tract_metrics
            assert "mape" in tract_metrics
            assert "n" in tract_metrics

    def test_no_segment_col(self, trained_model_and_data) -> None:
        """When segment_col=None, no segment_metrics key."""
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df, segment_col=None)
        assert "segment_metrics" not in metrics
