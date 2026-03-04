"""Tests for pricepoint.models.selection."""

import numpy as np
import pandas as pd

from pricepoint.models.selection import (
    CORRELATION_THRESHOLD,
    MIN_PERMUTATION_IMPORTANCE,
    drop_correlated,
    select_features,
)


class TestDropCorrelated:
    """Tests for drop_correlated."""

    def test_drops_perfectly_correlated(self) -> None:
        rng = np.random.RandomState(42)
        x = pd.DataFrame(
            {
                "a": rng.uniform(0, 100, 100),
                "b": np.arange(100, dtype=float),
            }
        )
        x["c"] = x["b"] * 2 + 1  # perfectly correlated with b
        result = drop_correlated(x, threshold=0.90)
        # One of b/c should be dropped
        assert result.shape[1] < x.shape[1]
        assert not ({"b", "c"}.issubset(result.columns))

    def test_keeps_uncorrelated(self) -> None:
        rng = np.random.RandomState(42)
        x = pd.DataFrame(
            {
                "a": rng.uniform(0, 100, 100),
                "b": rng.uniform(0, 100, 100),
                "c": rng.uniform(0, 100, 100),
            }
        )
        result = drop_correlated(x, threshold=0.90)
        assert result.shape[1] == 3

    def test_preserves_categorical_columns(self) -> None:
        rng = np.random.RandomState(42)
        x = pd.DataFrame(
            {
                "a": rng.uniform(0, 100, 100),
                "cat": pd.Categorical(rng.choice(["x", "y", "z"], 100)),
            }
        )
        result = drop_correlated(x)
        assert "cat" in result.columns

    def test_single_column(self) -> None:
        x = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        result = drop_correlated(x)
        assert list(result.columns) == ["a"]

    def test_threshold_constant(self) -> None:
        assert CORRELATION_THRESHOLD == 0.90

    def test_min_importance_constant(self) -> None:
        assert MIN_PERMUTATION_IMPORTANCE == 0.0


class TestSelectFeatures:
    """Tests for select_features."""

    def test_returns_dataframe(self) -> None:
        rng = np.random.RandomState(42)
        x = pd.DataFrame(
            {
                "a": rng.uniform(0, 100, 50),
                "b": rng.uniform(0, 100, 50),
            }
        )
        result = select_features(x)
        assert isinstance(result, pd.DataFrame)

    def test_custom_threshold(self) -> None:
        rng = np.random.RandomState(42)
        x = pd.DataFrame(
            {
                "a": np.arange(100, dtype=float),
                "b": np.arange(100, dtype=float) * 1.5 + rng.normal(0, 1, 100),
            }
        )
        # With threshold=0.5, highly correlated cols should be dropped
        result_strict = select_features(x, correlation_threshold=0.5)
        result_loose = select_features(x, correlation_threshold=0.999)
        assert result_strict.shape[1] <= result_loose.shape[1]
