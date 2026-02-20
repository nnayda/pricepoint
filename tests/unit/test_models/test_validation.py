"""Tests for pricepoint.models.validation."""

import pandas as pd
import pytest

from pricepoint.models.validation import cross_validate


class TestCrossValidate:
    """Tests for cross_validate."""

    def test_returns_expected_keys(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3)
        expected_keys = {"mae_mean", "mae_std", "rmse_mean", "rmse_std", "r2_mean", "r2_std"}
        assert expected_keys == set(result.keys())

    def test_values_are_floats(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3)
        for value in result.values():
            assert isinstance(value, float)

    def test_r2_mean_is_positive(self, synthetic_df: pd.DataFrame) -> None:
        result = cross_validate(features=synthetic_df, n_splits=3)
        # With a clear linear signal, mean R² should be positive
        assert result["r2_mean"] > 0.0

    def test_missing_target_raises(self, synthetic_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Target column"):
            cross_validate(features=synthetic_df, target_col="missing")
