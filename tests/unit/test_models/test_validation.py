"""Tests for pricepoint.models.validation."""

import pandas as pd
import pytest

from pricepoint.models.validation import cross_validate


class TestCrossValidate:
    """Tests for cross_validate."""

    def test_returns_expected_keys(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3, log_transform_target=False)
        expected_keys = {"mae_mean", "mae_std", "rmse_mean", "rmse_std", "r2_mean", "r2_std"}
        assert expected_keys.issubset(set(result.keys()))

    def test_values_are_floats(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3, log_transform_target=False)
        for key in ("mae_mean", "mae_std", "rmse_mean", "rmse_std", "r2_mean", "r2_std"):
            assert isinstance(result[key], float)

    def test_r2_mean_is_positive(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3, log_transform_target=False)
        assert result["r2_mean"] > 0.0

    def test_missing_target_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            cross_validate(features=synthetic_df, target_col="missing")

    def test_log_transform_target(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3, log_transform_target=True)
        assert result["mae_mean"] > 0
        assert result["rmse_mean"] > 0

    def test_temporal_mode(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(
            features=synthetic_df, n_splits=3, temporal=True, log_transform_target=False
        )
        assert "mae_mean" in result
        assert result["mae_mean"] > 0

    def test_importance_stability(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3, log_transform_target=False)
        assert "importance_stability" in result
        assert -1.0 <= result["importance_stability"] <= 1.0
