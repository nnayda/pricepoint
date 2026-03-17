"""Evaluation plot generation for MLflow artifact logging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MAX_SHAP_SAMPLES = 1000
_LEARNING_CURVE_MAX_ROWS = 10_000
_TOP_PDP_FEATURES = 6
_DPI = 150


def generate_evaluation_plots(
    *,
    model: Any,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    feature_importance: dict[str, float] | None = None,
    cv_metrics: dict[str, Any] | None = None,
    x_test: pd.DataFrame | None = None,
    segment_metrics: dict[str, dict[str, float]] | None = None,
    price_tier_metrics: dict[str, dict[str, float]] | None = None,
    output_dir: Path,
) -> list[Path]:
    """Generate all evaluation plots and save to *output_dir*.

    Returns a list of paths to generated PNG files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    preds = {"y_true": y_true, "y_pred": y_pred}
    generators = [
        (
            "feature_importance.png",
            _plot_feature_importance,
            {"feature_importance": feature_importance},
        ),
        ("actual_vs_predicted.png", _plot_actual_vs_predicted, preds),
        ("residuals_vs_predicted.png", _plot_residuals_vs_predicted, preds),
        ("residuals_distribution.png", _plot_residuals_distribution, preds),
        ("cv_fold_comparison.png", _plot_cv_fold_comparison, {"cv_metrics": cv_metrics}),
        ("shap_summary.png", _plot_shap_summary, {"model": model, "x_test": x_test}),
        (
            "partial_dependence.png",
            _plot_partial_dependence,
            {"model": model, "x_test": x_test, "feature_importance": feature_importance},
        ),
        ("shap_force.png", _plot_shap_force, {"model": model, "x_test": x_test, "y_pred": y_pred}),
        (
            "learning_curves.png",
            _plot_learning_curves,
            {"model": model, "x_test": x_test, "y_true": y_true},
        ),
        (
            "interval_calibration.png",
            _plot_interval_calibration,
            preds,
        ),
        (
            "segment_error.png",
            _plot_segment_error,
            {"segment_metrics": segment_metrics},
        ),
        (
            "scale_location.png",
            _plot_scale_location,
            preds,
        ),
        (
            "price_tier_errors.png",
            _plot_price_tier_errors,
            {"y_true": y_true, "y_pred": y_pred, "price_tier_metrics": price_tier_metrics},
        ),
        (
            "model_tree.png",
            _plot_model_tree,
            {"model": model},
        ),
    ]

    for filename, func, kwargs in generators:
        try:
            path = func(output_dir=output_dir, filename=filename, **kwargs)  # type: ignore[operator]
            if path is not None:
                paths.append(path)
        except Exception:
            logger.warning("Failed to generate plot %s", filename, exc_info=True)

    return paths


def _plot_feature_importance(
    *,
    feature_importance: dict[str, float] | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if not feature_importance:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sorted_items = sorted(feature_importance.items(), key=lambda x: x[1])
    names = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(10, max(6, len(names) * 0.35)))
    ax.barh(names, values, color="#2196F3")
    ax.set_xlabel("Gain")
    ax.set_title("Top Feature Importances (by Gain)")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_actual_vs_predicted(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import r2_score

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(y_true, y_pred, alpha=0.4, s=10, color="#2196F3")

    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=1.5, label="Ideal (y=x)")

    r2 = r2_score(y_true, y_pred)
    bbox = {"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5}
    ax.annotate(
        f"R² = {r2:.4f}",
        xy=(0.05, 0.95),
        xycoords="axes fraction",
        fontsize=12,
        verticalalignment="top",
        bbox=bbox,
    )

    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title("Actual vs Predicted")
    ax.legend()
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_residuals_vs_predicted(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    residuals = y_true - y_pred

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(y_pred, residuals, alpha=0.4, s=10, color="#FF9800")
    ax.axhline(y=0, color="r", linestyle="--", linewidth=1.5)

    ax.set_xlabel("Predicted")
    ax.set_ylabel("Residual (Actual - Predicted)")
    ax.set_title("Residuals vs Predicted")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_residuals_distribution(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    residuals = y_true - y_pred

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(residuals, bins=50, color="#4CAF50", edgecolor="black", alpha=0.7)

    mean_r = float(np.mean(residuals))
    median_r = float(np.median(residuals))
    std_r = float(np.std(residuals))

    ax.axvline(mean_r, color="red", linestyle="--", linewidth=1.5, label=f"Mean: {mean_r:,.0f}")
    ax.axvline(
        median_r,
        color="blue",
        linestyle="--",
        linewidth=1.5,
        label=f"Median: {median_r:,.0f}",
    )

    ax.annotate(
        f"Std: {std_r:,.0f}",
        xy=(0.95, 0.95),
        xycoords="axes fraction",
        fontsize=11,
        horizontalalignment="right",
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )

    ax.set_xlabel("Residual")
    ax.set_ylabel("Frequency")
    ax.set_title("Residuals Distribution")
    ax.legend()
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_cv_fold_comparison(
    *,
    cv_metrics: dict[str, Any] | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if not cv_metrics:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Extract metric pairs: look for mean/std keys
    metric_names = []
    means = []
    stds = []
    for base in ("mae", "rmse", "r2"):
        mean_key = f"{base}_mean"
        std_key = f"{base}_std"
        if mean_key in cv_metrics and std_key in cv_metrics:
            metric_names.append(base.upper())
            means.append(cv_metrics[mean_key])
            stds.append(cv_metrics[std_key])

    if not metric_names:
        return None

    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(metric_names))
    bars = ax.bar(x, means, yerr=stds, capsize=5, color="#9C27B0", alpha=0.8, edgecolor="black")

    for bar, mean, std in zip(bars, means, stds, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + std + 0.01 * abs(max(means)),
            f"{mean:.2f}\n(+/-{std:.2f})",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(metric_names)
    ax.set_title("Cross-Validation Fold Comparison (Mean +/- Std)")
    ax.set_ylabel("Score")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_shap_summary(
    *,
    model: Any,
    x_test: pd.DataFrame | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if x_test is None:
        return None
    try:
        import shap
    except ImportError:
        logger.info("shap not installed, skipping SHAP summary plot")
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sample = x_test.sample(n=min(len(x_test), _MAX_SHAP_SAMPLES), random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    fig, ax = plt.subplots(figsize=(10, 8))
    shap.summary_plot(shap_values, sample, show=False, max_display=20)

    path = output_dir / filename
    plt.savefig(path, dpi=_DPI, bbox_inches="tight")
    plt.close("all")
    return path


def _plot_partial_dependence(
    *,
    model: Any,
    x_test: pd.DataFrame | None,
    feature_importance: dict[str, float] | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if x_test is None or not feature_importance:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.inspection import PartialDependenceDisplay

    # Get top N numeric features that exist in x_test (PDP requires numeric)
    numeric_cols = set(x_test.select_dtypes(include="number").columns)
    sorted_feats = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    top_features = [f for f, _ in sorted_feats if f in numeric_cols][:_TOP_PDP_FEATURES]

    if not top_features:
        return None

    sample = x_test.sample(n=min(len(x_test), _LEARNING_CURVE_MAX_ROWS), random_state=42)

    fig, axes = plt.subplots(
        nrows=2,
        ncols=3,
        figsize=(18, 10),
        constrained_layout=True,
    )
    # Pad with None if fewer than 6 features
    flat_axes = axes.flatten()

    PartialDependenceDisplay.from_estimator(
        model,
        sample,
        top_features,
        ax=flat_axes[: len(top_features)],
        kind="average",
        grid_resolution=50,
    )

    # Hide unused axes
    for i in range(len(top_features), len(flat_axes)):
        flat_axes[i].set_visible(False)

    fig.suptitle("Partial Dependence Plots (Top Features)", fontsize=14)

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_shap_force(
    *,
    model: Any,
    x_test: pd.DataFrame | None,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if x_test is None:
        return None
    try:
        import shap
    except ImportError:
        logger.info("shap not installed, skipping SHAP force plot")
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Pick the sample closest to the median prediction
    median_pred = float(np.median(y_pred))
    idx = int(np.argmin(np.abs(y_pred - median_pred)))

    explainer = shap.TreeExplainer(model)
    sample = x_test.iloc[[idx]]
    shap_values = explainer.shap_values(sample)

    fig, ax = plt.subplots(figsize=(14, 4))
    shap.waterfall_plot(
        shap.Explanation(
            values=shap_values[0],
            base_values=explainer.expected_value,
            data=sample.iloc[0].values,
            feature_names=list(sample.columns),
        ),
        show=False,
    )

    path = output_dir / filename
    plt.savefig(path, dpi=_DPI, bbox_inches="tight")
    plt.close("all")
    return path


def _plot_learning_curves(
    *,
    model: Any,
    x_test: pd.DataFrame | None,
    y_true: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    if x_test is None:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.model_selection import learning_curve

    # Sample down for performance
    n = len(x_test)
    if n > _LEARNING_CURVE_MAX_ROWS:
        rng = np.random.RandomState(42)
        indices = rng.choice(n, _LEARNING_CURVE_MAX_ROWS, replace=False)
        x_sample = x_test.iloc[indices]
        y_sample = y_true[indices]
    else:
        x_sample = x_test
        y_sample = y_true

    # Clone model without early_stopping_rounds so sklearn's learning_curve
    # can fit without requiring eval_set.
    from sklearn.base import clone

    lc_model = clone(model)
    lc_model.set_params(early_stopping_rounds=None)

    train_sizes, train_scores, val_scores = learning_curve(
        lc_model,
        x_sample,
        y_sample,
        cv=5,
        scoring="r2",
        train_sizes=np.linspace(0.1, 1.0, 8),
        n_jobs=-1,
    )

    train_mean = train_scores.mean(axis=1)
    train_std = train_scores.std(axis=1)
    val_mean = val_scores.mean(axis=1)
    val_std = val_scores.std(axis=1)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.fill_between(
        train_sizes,
        train_mean - train_std,
        train_mean + train_std,
        alpha=0.1,
        color="blue",
    )
    ax.fill_between(
        train_sizes,
        val_mean - val_std,
        val_mean + val_std,
        alpha=0.1,
        color="orange",
    )
    ax.plot(train_sizes, train_mean, "o-", color="blue", label="Training score")
    ax.plot(train_sizes, val_mean, "o-", color="orange", label="Validation score")

    ax.set_xlabel("Training Set Size")
    ax.set_ylabel("R² Score")
    ax.set_title("Learning Curves")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_interval_calibration(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Plot expected vs actual coverage of prediction intervals."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mape = float(np.mean(np.abs((y_true - y_pred) / np.where(y_true != 0, y_true, 1.0))) * 100)

    coverage_levels = [50, 70, 80, 90, 95]
    actual_coverages: list[float] = []

    for level in coverage_levels:
        margin = np.abs(y_pred) * (level / 100.0) * (mape / 100.0)
        low = y_pred - margin
        high = y_pred + margin
        covered = ((y_true >= low) & (y_true <= high)).mean()
        actual_coverages.append(float(covered * 100))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(coverage_levels, coverage_levels, "r--", linewidth=1.5, label="Ideal (diagonal)")
    ax.plot(coverage_levels, actual_coverages, "bo-", linewidth=2, label="Actual coverage")

    ax.set_xlabel("Expected Coverage (%)")
    ax.set_ylabel("Actual Coverage (%)")
    ax.set_title("Prediction Interval Calibration")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(40, 100)
    ax.set_ylim(0, 105)
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_segment_error(
    *,
    segment_metrics: dict[str, dict[str, float]] | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Bar chart of top-10 worst-performing segments by MAE."""
    if not segment_metrics:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sorted_segs = sorted(segment_metrics.items(), key=lambda x: x[1]["mae"], reverse=True)
    top10 = sorted_segs[:10]

    names = [s for s, _ in top10]
    maes = [m["mae"] for _, m in top10]

    fig, ax = plt.subplots(figsize=(10, max(6, len(names) * 0.5)))
    ax.barh(names, maes, color="#E91E63")
    ax.set_xlabel("MAE ($)")
    ax.set_title("Top 10 Worst-Performing Census Tracts by MAE")
    ax.invert_yaxis()
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_scale_location(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Scale-location plot: sqrt(|residuals|) vs predicted with binned-mean trend."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    residuals = y_true - y_pred
    sqrt_abs_resid = np.sqrt(np.abs(residuals))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(y_pred, sqrt_abs_resid, alpha=0.4, s=10, color="#FF9800")

    # Binned-mean trend line
    n_bins = min(20, max(5, len(y_pred) // 20))
    bin_edges = np.linspace(y_pred.min(), y_pred.max(), n_bins + 1)
    bin_centers = []
    bin_means = []
    for i in range(n_bins):
        if i == n_bins - 1:
            mask = (y_pred >= bin_edges[i]) & (y_pred <= bin_edges[i + 1])
        else:
            mask = (y_pred >= bin_edges[i]) & (y_pred < bin_edges[i + 1])
        if mask.sum() > 0:
            bin_centers.append(float((bin_edges[i] + bin_edges[i + 1]) / 2))
            bin_means.append(float(sqrt_abs_resid[mask].mean()))

    if bin_centers:
        ax.plot(bin_centers, bin_means, "r-o", linewidth=2, markersize=5, label="Binned mean")
        ax.legend()

    ax.set_xlabel("Predicted")
    ax.set_ylabel("√|Residual|")
    ax.set_title("Scale-Location Plot")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_price_tier_errors(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    price_tier_metrics: dict[str, dict[str, float]] | None,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Box plot of absolute percentage errors by price quartile."""
    if len(y_true) < 4:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Compute absolute percentage errors
    mask = y_true != 0
    ape = np.full_like(y_true, np.nan)
    ape[mask] = np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]) * 100

    quartile_edges = np.percentile(y_true, [0, 25, 50, 75, 100])
    tier_labels = ["Q1\n(Bottom 25%)", "Q2\n(25-50%)", "Q3\n(50-75%)", "Q4\n(Top 25%)"]
    tier_indices = np.digitize(y_true, quartile_edges[1:-1], right=True)

    data: list[np.ndarray] = []
    labels: list[str] = []
    medians: list[float] = []
    for tier_idx, label in enumerate(tier_labels):
        tier_mask = (tier_indices == tier_idx) & ~np.isnan(ape)
        if tier_mask.sum() > 0:
            tier_ape = ape[tier_mask]
            data.append(tier_ape)
            labels.append(label)
            medians.append(float(np.median(tier_ape)))

    if not data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, showfliers=False)

    colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63"]
    for patch, color in zip(bp["boxes"], colors[: len(data)], strict=False):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Label medians
    for i, med in enumerate(medians):
        ax.text(i + 1, med, f"  {med:.1f}%", va="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("Absolute Percentage Error (%)")
    ax.set_title("Prediction Error by Price Quartile")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_model_tree(
    *,
    model: Any,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Render the first tree from an XGBoost model."""
    try:
        import xgboost
    except ImportError:
        logger.info("xgboost not installed, skipping model tree plot")
        return None

    if not isinstance(model, xgboost.XGBRegressor):
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(24, 14))
    xgboost.plot_tree(model, num_trees=0, ax=ax)
    ax.set_title("XGBoost — First Tree (tree 0)")

    path = output_dir / filename
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path
