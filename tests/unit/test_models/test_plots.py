"""Tests for pricepoint.models.plots."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from pricepoint.models.plots import (
    _plot_actual_vs_predicted,
    _plot_cv_fold_comparison,
    _plot_feature_importance,
    _plot_learning_curves,
    _plot_partial_dependence,
    _plot_residuals_distribution,
    _plot_residuals_vs_predicted,
    _plot_shap_force,
    _plot_shap_summary,
    generate_evaluation_plots,
)
from pricepoint.models.training import train_model


@pytest.fixture()
def eval_data(synthetic_df: pd.DataFrame):
    """Produce a trained model and evaluation arrays."""
    model = train_model(features=synthetic_df)
    x = synthetic_df.drop(columns=["sold_price"])
    if hasattr(model, "feature_names_in_"):
        x = x[list(model.feature_names_in_)]
    y_true = synthetic_df["sold_price"].values.astype(np.float64)
    y_pred = model.predict(x).astype(np.float64)
    importance = model.get_booster().get_score(importance_type="gain")
    sorted_imp = dict(sorted(importance.items(), key=lambda i: i[1], reverse=True)[:20])
    return model, y_true, y_pred, x, sorted_imp


class TestPlotHelpers:
    """Test each private plot helper produces a file."""

    def test_feature_importance(self, eval_data, tmp_path: Path) -> None:
        _, _, _, _, importance = eval_data
        path = _plot_feature_importance(
            feature_importance=importance, output_dir=tmp_path, filename="fi.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_feature_importance_none(self, tmp_path: Path) -> None:
        path = _plot_feature_importance(
            feature_importance=None, output_dir=tmp_path, filename="fi.png"
        )
        assert path is None

    def test_actual_vs_predicted(self, eval_data, tmp_path: Path) -> None:
        _, y_true, y_pred, _, _ = eval_data
        path = _plot_actual_vs_predicted(
            y_true=y_true, y_pred=y_pred, output_dir=tmp_path, filename="avp.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_residuals_vs_predicted(self, eval_data, tmp_path: Path) -> None:
        _, y_true, y_pred, _, _ = eval_data
        path = _plot_residuals_vs_predicted(
            y_true=y_true, y_pred=y_pred, output_dir=tmp_path, filename="rvp.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_residuals_distribution(self, eval_data, tmp_path: Path) -> None:
        _, y_true, y_pred, _, _ = eval_data
        path = _plot_residuals_distribution(
            y_true=y_true, y_pred=y_pred, output_dir=tmp_path, filename="rd.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_cv_fold_comparison(self, tmp_path: Path) -> None:
        cv = {"mae_mean": 1000.0, "mae_std": 100.0, "rmse_mean": 1500.0, "rmse_std": 150.0,
              "r2_mean": 0.95, "r2_std": 0.02}
        path = _plot_cv_fold_comparison(
            cv_metrics=cv, output_dir=tmp_path, filename="cv.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_cv_fold_comparison_none(self, tmp_path: Path) -> None:
        path = _plot_cv_fold_comparison(
            cv_metrics=None, output_dir=tmp_path, filename="cv.png"
        )
        assert path is None

    def test_partial_dependence(self, eval_data, tmp_path: Path) -> None:
        model, _, _, x_test, importance = eval_data
        path = _plot_partial_dependence(
            model=model, x_test=x_test, feature_importance=importance,
            output_dir=tmp_path, filename="pdp.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_learning_curves(self, eval_data, tmp_path: Path) -> None:
        model, y_true, _, x_test, _ = eval_data
        path = _plot_learning_curves(
            model=model, x_test=x_test, y_true=y_true,
            output_dir=tmp_path, filename="lc.png"
        )
        assert path is not None
        assert path.stat().st_size > 0

    def test_shap_summary_skipped_without_shap(self, eval_data, tmp_path: Path) -> None:
        model, _, _, x_test, _ = eval_data
        with patch.dict("sys.modules", {"shap": None}):
            path = _plot_shap_summary(
                model=model, x_test=x_test, output_dir=tmp_path, filename="shap.png"
            )
        assert path is None

    def test_shap_force_skipped_without_shap(self, eval_data, tmp_path: Path) -> None:
        model, _, y_pred, x_test, _ = eval_data
        with patch.dict("sys.modules", {"shap": None}):
            path = _plot_shap_force(
                model=model, x_test=x_test, y_pred=y_pred,
                output_dir=tmp_path, filename="shap_force.png"
            )
        assert path is None


class TestGenerateEvaluationPlots:
    """Test the main entry point."""

    def test_returns_expected_plots(self, eval_data, tmp_path: Path) -> None:
        model, y_true, y_pred, x_test, importance = eval_data
        cv = {"mae_mean": 1000.0, "mae_std": 100.0, "rmse_mean": 1500.0, "rmse_std": 150.0,
              "r2_mean": 0.95, "r2_std": 0.02}
        paths = generate_evaluation_plots(
            model=model,
            y_true=y_true,
            y_pred=y_pred,
            feature_importance=importance,
            cv_metrics=cv,
            x_test=x_test,
            output_dir=tmp_path,
        )
        # Without shap: feature_importance, actual_vs_predicted, residuals_vs_predicted,
        # residuals_distribution, cv_fold_comparison, partial_dependence, learning_curves = 7
        assert len(paths) >= 7
        for p in paths:
            assert p.exists()
            assert p.stat().st_size > 0

    def test_works_without_optional_data(self, eval_data, tmp_path: Path) -> None:
        model, y_true, y_pred, _, _ = eval_data
        paths = generate_evaluation_plots(
            model=model,
            y_true=y_true,
            y_pred=y_pred,
            output_dir=tmp_path,
        )
        # Should still produce actual_vs_predicted, residuals_vs_predicted, residuals_distribution
        assert len(paths) >= 3
