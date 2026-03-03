"""Tests for pricepoint.models.evaluation."""

import pandas as pd
import pytest

from pricepoint.models.evaluation import evaluate_model
from pricepoint.models.training import train_model


@pytest.fixture()
def trained_model_and_data(synthetic_df: pd.DataFrame):
    """Train a model and return it along with test data."""
    model = train_model(features=synthetic_df)
    # Use full df as test data for deterministic evaluation
    return model, synthetic_df


class TestEvaluateModel:
    """Tests for evaluate_model."""

    def test_returns_expected_keys(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df)
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "mape" in metrics
        assert "r2" in metrics
        assert "median_ae" in metrics

    def test_metrics_are_numeric(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df)
        for key in ("mae", "rmse", "mape", "r2", "median_ae"):
            assert isinstance(metrics[key], float)

    def test_feature_importance_included(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df)
        assert "feature_importance_top20" in metrics
        assert isinstance(metrics["feature_importance_top20"], dict)
        assert len(metrics["feature_importance_top20"]) > 0

    def test_r2_is_reasonable(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df)
        # On training data, R² should be high
        assert metrics["r2"] > 0.9

    def test_prediction_arrays_included(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        metrics = evaluate_model(model=model, test_features=df)
        assert "_y_true" in metrics
        assert "_y_pred" in metrics
        assert "_x_test" in metrics
        import numpy as np

        assert isinstance(metrics["_y_true"], np.ndarray)
        assert isinstance(metrics["_y_pred"], np.ndarray)
        assert isinstance(metrics["_x_test"], pd.DataFrame)
        assert len(metrics["_y_true"]) == len(metrics["_y_pred"])

    def test_missing_target_raises(self, trained_model_and_data) -> None:
        model, df = trained_model_and_data
        with pytest.raises(ValueError, match="Target column"):
            evaluate_model(model=model, test_features=df, target_col="nonexistent")
