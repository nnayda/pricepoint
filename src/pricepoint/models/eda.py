"""Exploratory data analysis metrics and plots for MLflow training runs.

Computes summary statistics about the training data and generates
distribution/correlation plots logged as artifacts alongside model evaluation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

_DPI = 150


def compute_eda_metrics(
    x: pd.DataFrame,
    y: pd.Series,
    *,
    log_transformed: bool = True,
) -> dict[str, float]:
    """Compute scalar EDA metrics about the training data.

    All keys are prefixed with ``data.`` so they can be merged directly
    into the MLflow metrics dict without collision.

    Parameters
    ----------
    x : pd.DataFrame
        Feature matrix (no target column).
    y : pd.Series
        Target variable (may be log1p-transformed).
    log_transformed : bool
        If True, ``y`` is in log-space and will be converted back to
        dollar-space via ``expm1`` for target statistics.

    Returns
    -------
    dict[str, float]
        19 scalar metrics with ``data.`` prefix.
    """
    y_dollar = np.expm1(y) if log_transformed else y

    numeric_cols = x.select_dtypes(include="number")
    cat_cols = x.select_dtypes(include="category")

    # Shape metrics
    metrics: dict[str, float] = {
        "data.n_rows": float(len(x)),
        "data.n_features": float(x.shape[1]),
        "data.n_numeric_features": float(numeric_cols.shape[1]),
        "data.n_categorical_features": float(cat_cols.shape[1]),
    }

    # Null metrics
    null_rates = x.isna().mean()
    metrics["data.null_rate_mean"] = float(null_rates.mean())
    metrics["data.null_rate_max"] = float(null_rates.max()) if len(null_rates) > 0 else 0.0
    metrics["data.n_features_with_nulls"] = float((null_rates > 0).sum())

    # Target metrics (dollar-space)
    y_arr = (
        y_dollar.to_numpy(dtype=np.float64)
        if isinstance(y_dollar, pd.Series)
        else np.asarray(y_dollar, dtype=np.float64)
    )
    metrics["data.target_mean"] = float(np.mean(y_arr))
    metrics["data.target_median"] = float(np.median(y_arr))
    metrics["data.target_std"] = float(np.std(y_arr))
    metrics["data.target_p05"] = float(np.percentile(y_arr, 5))
    metrics["data.target_p25"] = float(np.percentile(y_arr, 25))
    metrics["data.target_p75"] = float(np.percentile(y_arr, 75))
    metrics["data.target_p95"] = float(np.percentile(y_arr, 95))
    metrics["data.target_skew"] = float(stats.skew(y_arr))
    metrics["data.target_kurtosis"] = float(stats.kurtosis(y_arr))

    # Feature-level metrics
    if numeric_cols.shape[1] > 0:
        variances = numeric_cols.var()
        metrics["data.feature_variance_mean"] = float(variances.mean())
        metrics["data.feature_variance_min"] = float(variances.min())
        near_constant = (variances < 1e-10).sum()
        metrics["data.n_near_constant_features"] = float(near_constant)
    else:
        metrics["data.feature_variance_mean"] = 0.0
        metrics["data.feature_variance_min"] = 0.0
        metrics["data.n_near_constant_features"] = 0.0

    # Max absolute correlation among numeric features
    if numeric_cols.shape[1] >= 2:
        corr = numeric_cols.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
        max_corr = upper.max().max()
        metrics["data.max_abs_correlation"] = float(max_corr) if not np.isnan(max_corr) else 0.0
    else:
        metrics["data.max_abs_correlation"] = 0.0

    return metrics


def generate_eda_plots(
    x: pd.DataFrame,
    y: pd.Series,
    *,
    log_transformed: bool = True,
    output_dir: Path,
) -> list[Path]:
    """Generate EDA plots and save to *output_dir*.

    Returns a list of paths to generated PNG files. Individual plot
    failures are logged but do not prevent other plots from generating.

    Parameters
    ----------
    x : pd.DataFrame
        Feature matrix (no target column).
    y : pd.Series
        Target variable (may be log1p-transformed).
    log_transformed : bool
        If True, ``y`` is converted to dollar-space for the target plot.
    output_dir : Path
        Directory to write PNG files into.

    Returns
    -------
    list[Path]
        Paths to generated PNG files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    target_kwargs = {"y": y, "log_transformed": log_transformed}
    pairwise_kwargs = {"x": x, **target_kwargs}
    generators = [
        ("eda_target_distribution.png", _plot_target_distribution, target_kwargs),
        ("eda_feature_nulls.png", _plot_feature_nulls, {"x": x}),
        ("eda_correlation_heatmap.png", _plot_correlation_heatmap, {"x": x}),
        ("eda_numeric_distributions.png", _plot_numeric_distributions, {"x": x}),
        ("eda_categorical_balance.png", _plot_categorical_balance, {"x": x}),
        ("eda_pairwise_target.png", _plot_pairwise_target, pairwise_kwargs),
    ]

    for filename, func, kwargs in generators:
        try:
            path = func(output_dir=output_dir, filename=filename, **kwargs)  # type: ignore[operator]
            if path is not None:
                paths.append(path)
        except Exception:
            logger.warning("Failed to generate EDA plot %s", filename, exc_info=True)

    return paths


def _plot_target_distribution(
    *,
    y: pd.Series,
    log_transformed: bool,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Histogram of sold_price in dollar-space with mean/median lines."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_dollar = np.expm1(y) if log_transformed else y

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(y_dollar, bins=50, color="#4CAF50", edgecolor="black", alpha=0.7)

    mean_val = float(np.mean(y_dollar))
    median_val = float(np.median(y_dollar))
    mean_label = f"Mean: ${mean_val:,.0f}"
    median_label = f"Median: ${median_val:,.0f}"
    ax.axvline(mean_val, color="red", linestyle="--", linewidth=1.5, label=mean_label)
    ax.axvline(median_val, color="blue", linestyle="--", linewidth=1.5, label=median_label)

    ax.set_xlabel("Sold Price ($)")
    ax.set_ylabel("Frequency")
    ax.set_title("Target Distribution (Sold Price)")
    ax.legend()
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_feature_nulls(
    *,
    x: pd.DataFrame,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Horizontal bar chart of top-20 features by null rate."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    null_rates = x.isna().mean()
    null_rates = null_rates[null_rates > 0].sort_values(ascending=False).head(20)

    if null_rates.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, max(4, len(null_rates) * 0.4)))
    ax.barh(null_rates.index.tolist(), null_rates.values, color="#FF9800")
    ax.set_xlabel("Null Rate")
    ax.set_title("Top Features by Null Rate")
    ax.invert_yaxis()
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_correlation_heatmap(
    *,
    x: pd.DataFrame,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """Clustered heatmap of top-20 most-correlated numeric feature pairs."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    numeric = x.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return None

    corr = numeric.corr()

    # Find the 20 features involved in the highest absolute correlations
    abs_corr = corr.abs()
    upper = abs_corr.where(np.triu(np.ones(abs_corr.shape, dtype=bool), k=1))
    stacked = upper.stack().sort_values(ascending=False)
    top_features: list[str] = []
    seen: set[str] = set()
    for (f1, f2), _ in stacked.items():
        for f in (f1, f2):
            if f not in seen:
                top_features.append(f)
                seen.add(f)
            if len(top_features) >= 20:
                break
        if len(top_features) >= 20:
            break

    if len(top_features) < 2:
        return None

    sub_corr = corr.loc[top_features, top_features]

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(sub_corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(top_features)))
    ax.set_yticks(range(len(top_features)))
    ax.set_xticklabels(top_features, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(top_features, fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Feature Correlation Heatmap (Top 20)")
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_numeric_distributions(
    *,
    x: pd.DataFrame,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """3x4 grid of histograms for the top-12 numeric features by variance."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    numeric = x.select_dtypes(include="number")
    if numeric.shape[1] == 0:
        return None

    variances = numeric.var().sort_values(ascending=False)
    top_cols = variances.head(12).index.tolist()

    nrows, ncols = 3, 4
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(16, 10))
    flat_axes = axes.flatten()

    for i, col in enumerate(top_cols):
        ax = flat_axes[i]
        data = numeric[col].dropna()
        ax.hist(data, bins=30, color="#2196F3", edgecolor="black", alpha=0.7)
        ax.set_title(col, fontsize=9)
        ax.tick_params(labelsize=7)

    # Hide unused axes
    for i in range(len(top_cols), len(flat_axes)):
        flat_axes[i].set_visible(False)

    fig.suptitle("Numeric Feature Distributions (Top 12 by Variance)", fontsize=13)
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_categorical_balance(
    *,
    x: pd.DataFrame,
    output_dir: Path,
    filename: str,
) -> Path | None:
    """2x3 grid of value-count bar charts for categorical features."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cat_cols = x.select_dtypes(include="category").columns.tolist()
    if not cat_cols:
        return None

    # Take up to 6 categorical features
    cat_cols = cat_cols[:6]

    nrows, ncols = 2, 3
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, 8))
    flat_axes = axes.flatten()

    for i, col in enumerate(cat_cols):
        ax = flat_axes[i]
        counts = x[col].value_counts().head(10)
        ax.bar(range(len(counts)), counts.values, color="#9C27B0", edgecolor="black", alpha=0.8)
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(counts.index.tolist(), rotation=45, ha="right", fontsize=7)
        ax.set_title(col, fontsize=9)
        ax.tick_params(labelsize=7)

    for i in range(len(cat_cols), len(flat_axes)):
        flat_axes[i].set_visible(False)

    fig.suptitle("Categorical Feature Value Counts", fontsize=13)
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _plot_pairwise_target(
    *,
    x: pd.DataFrame,
    y: pd.Series,
    log_transformed: bool,
    output_dir: Path,
    filename: str,
    max_features: int = 12,
) -> Path | None:
    """Scatter plots of top numeric features vs target with regression trendlines.

    Selects features by highest absolute Pearson correlation with the target
    and plots each in a subplot grid with an OLS trendline.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_dollar = np.expm1(y) if log_transformed else y

    numeric = x.select_dtypes(include="number")
    if numeric.shape[1] == 0:
        return None

    # Rank features by absolute correlation with target
    correlations = numeric.corrwith(y_dollar).abs().dropna().sort_values(ascending=False)
    top_cols = correlations.head(max_features).index.tolist()

    if not top_cols:
        return None

    ncols = 3
    nrows = (len(top_cols) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(5 * ncols, 4 * nrows))
    flat_axes = np.array(axes).flatten() if nrows > 1 or ncols > 1 else [axes]

    for i, col in enumerate(top_cols):
        ax = flat_axes[i]
        mask = numeric[col].notna() & y_dollar.notna()
        xi = numeric[col][mask].values
        yi = y_dollar[mask].values

        ax.scatter(xi, yi, alpha=0.35, s=12, color="#1976D2", edgecolors="none")

        # OLS trendline
        if len(xi) >= 2:
            coeffs = np.polyfit(xi, yi, 1)
            x_line = np.linspace(xi.min(), xi.max(), 100)
            ax.plot(x_line, np.polyval(coeffs, x_line), color="#D32F2F", linewidth=1.5)

        corr_val = correlations.get(col, 0.0)
        ax.set_title(f"{col}  (r={corr_val:.2f})", fontsize=9)
        ax.set_xlabel(col, fontsize=8)
        ax.set_ylabel("Sold Price ($)", fontsize=8)
        ax.tick_params(labelsize=7)

    for i in range(len(top_cols), len(flat_axes)):
        flat_axes[i].set_visible(False)

    fig.suptitle("Feature vs Target (Top by Correlation)", fontsize=13)
    fig.tight_layout()

    path = output_dir / filename
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path
