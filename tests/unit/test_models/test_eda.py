"""Tests for pricepoint.models.eda."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from pricepoint.models.eda import compute_eda_metrics, generate_eda_plots

_EXPECTED_KEYS = {
    "data.n_rows",
    "data.n_features",
    "data.n_numeric_features",
    "data.n_categorical_features",
    "data.null_rate_mean",
    "data.null_rate_max",
    "data.n_features_with_nulls",
    "data.target_mean",
    "data.target_median",
    "data.target_std",
    "data.target_p05",
    "data.target_p25",
    "data.target_p75",
    "data.target_p95",
    "data.target_skew",
    "data.target_kurtosis",
    "data.feature_variance_mean",
    "data.feature_variance_min",
    "data.n_near_constant_features",
    "data.max_abs_correlation",
}


@pytest.fixture()
def eda_xy() -> tuple[pd.DataFrame, pd.Series]:
    """Feature matrix and log-transformed target for EDA tests."""
    rng = np.random.RandomState(42)
    n = 100
    x = pd.DataFrame(
        {
            "sqft": rng.uniform(800, 4000, n),
            "bedrooms": rng.randint(1, 6, n).astype(float),
            "bathrooms": rng.randint(1, 4, n).astype(float),
            "lot_size": rng.uniform(2000, 20000, n),
            "year_built": rng.randint(1950, 2023, n).astype(float),
            "parking_type": pd.Categorical(rng.choice(["Attached", "Detached", "None"], n)),
        }
    )
    # Sprinkle some nulls
    x.loc[0:4, "lot_size"] = np.nan
    # log1p-transformed target
    y = pd.Series(np.log1p(50000 + 150 * x["sqft"].fillna(0) + rng.normal(0, 5000, n)))
    return x, y


class TestComputeEdaMetrics:
    def test_keys(self, eda_xy: tuple[pd.DataFrame, pd.Series]) -> None:
        x, y = eda_xy
        metrics = compute_eda_metrics(x, y, log_transformed=True)
        assert set(metrics.keys()) == _EXPECTED_KEYS

    def test_values_sane(self, eda_xy: tuple[pd.DataFrame, pd.Series]) -> None:
        x, y = eda_xy
        metrics = compute_eda_metrics(x, y, log_transformed=True)
        for key, val in metrics.items():
            assert isinstance(val, float), f"{key} is not float"
            assert not np.isnan(val), f"{key} is NaN"
        assert metrics["data.n_rows"] == 100.0
        assert metrics["data.n_features"] == 6.0
        assert metrics["data.n_numeric_features"] == 5.0
        assert metrics["data.n_categorical_features"] == 1.0
        assert metrics["data.n_features_with_nulls"] >= 1.0
        assert metrics["data.target_mean"] > 0

    def test_log_transform_conversion(self, eda_xy: tuple[pd.DataFrame, pd.Series]) -> None:
        x, y = eda_xy
        metrics_log = compute_eda_metrics(x, y, log_transformed=True)
        # Pretend y is already in dollar-space
        y_dollar = np.expm1(y)
        metrics_raw = compute_eda_metrics(x, y_dollar, log_transformed=False)
        # Target stats should be approximately equal
        np.testing.assert_allclose(
            metrics_log["data.target_mean"],
            metrics_raw["data.target_mean"],
            rtol=1e-5,
        )


class TestGenerateEdaPlots:
    def test_all_plots_generated(
        self, eda_xy: tuple[pd.DataFrame, pd.Series], tmp_path: Path
    ) -> None:
        x, y = eda_xy
        paths = generate_eda_plots(x, y, log_transformed=True, output_dir=tmp_path)
        filenames = {p.name for p in paths}
        # Target, nulls (has nulls), correlation, numeric distributions, categorical
        assert "eda_target_distribution.png" in filenames
        assert "eda_feature_nulls.png" in filenames
        assert "eda_correlation_heatmap.png" in filenames
        assert "eda_numeric_distributions.png" in filenames
        assert "eda_categorical_balance.png" in filenames
        assert len(paths) == 5
        for p in paths:
            assert p.stat().st_size > 0

    def test_no_nulls_skips_null_plot(self, tmp_path: Path) -> None:
        rng = np.random.RandomState(42)
        n = 50
        x = pd.DataFrame({"a": rng.uniform(0, 1, n), "b": rng.uniform(0, 1, n)})
        y = pd.Series(rng.uniform(100000, 500000, n))
        paths = generate_eda_plots(x, y, log_transformed=False, output_dir=tmp_path)
        filenames = {p.name for p in paths}
        assert "eda_feature_nulls.png" not in filenames
        # No categoricals either
        assert "eda_categorical_balance.png" not in filenames

    def test_failure_isolation(
        self, eda_xy: tuple[pd.DataFrame, pd.Series], tmp_path: Path
    ) -> None:
        x, y = eda_xy
        with patch(
            "pricepoint.models.eda._plot_correlation_heatmap",
            side_effect=RuntimeError("boom"),
        ):
            paths = generate_eda_plots(x, y, log_transformed=True, output_dir=tmp_path)
        filenames = {p.name for p in paths}
        assert "eda_correlation_heatmap.png" not in filenames
        # Other plots should still be generated
        assert "eda_target_distribution.png" in filenames

    def test_minimal_data(self, tmp_path: Path) -> None:
        """Single row, single numeric column — should not crash."""
        x = pd.DataFrame({"a": [1.0]})
        y = pd.Series([100000.0])
        paths = generate_eda_plots(x, y, log_transformed=False, output_dir=tmp_path)
        # Target distribution should always work; others may be skipped
        filenames = {p.name for p in paths}
        assert "eda_target_distribution.png" in filenames
