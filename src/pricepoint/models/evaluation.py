"""Model evaluation -- compute metrics on held-out test data."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)

logger = logging.getLogger(__name__)

TOP_N_FEATURES = 20


def _mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute MAPE, handling zero values in y_true."""
    mask = y_true != 0
    if not mask.any():
        return float("inf")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_model(
    *,
    model: Any,
    test_features: pd.DataFrame,
    target_col: str = "sold_price",
    segment_col: str | None = "census_tract_geoid",
) -> dict[str, Any]:
    """Evaluate a trained model on test data.

    Parameters
    ----------
    model : fitted model
        Must implement `predict()` and have `feature_names_in_` attribute.
    test_features : pd.DataFrame
        Test data including the target column.
    target_col : str
        Name of the target column.

    Returns
    -------
    dict
        Metric names to values including feature importances.
    """
    if target_col not in test_features.columns:
        msg = f"Target column '{target_col}' not found in test data"
        raise ValueError(msg)

    # Drop rows where target is NaN (unsold listings have no ground truth)
    test_features = test_features[test_features[target_col].notna()]

    # Extract segment column before dropping non-numeric columns
    segment_values: pd.Series | None = None
    if segment_col and segment_col in test_features.columns:
        segment_values = test_features[segment_col].copy()

    y_true = test_features[target_col].values
    x_test = test_features.drop(columns=[target_col])

    # Keep only the features the model was trained on
    if hasattr(model, "feature_names_in_"):
        trained_features = list(model.feature_names_in_)
        missing = set(trained_features) - set(x_test.columns)
        if missing:
            logger.warning("Missing features in test data (filling with NaN): %s", missing)
            for col in missing:
                x_test[col] = np.nan
        x_test = x_test[trained_features]

    y_pred = model.predict(x_test)

    # Inverse log-transform predictions if the model was trained on log1p(target).
    # y_true comes from the raw DataFrame (already in dollar-space).
    log_target = getattr(model, "log_target", False) is True
    if log_target:
        y_pred = np.expm1(y_pred)

    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_pred_arr = np.asarray(y_pred, dtype=np.float64)

    metrics: dict[str, Any] = {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "rmse": float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr))),
        "mape": _mean_absolute_percentage_error(y_true_arr, y_pred_arr),
        "r2": float(r2_score(y_true_arr, y_pred_arr)),
        "median_ae": float(median_absolute_error(y_true_arr, y_pred_arr)),
    }

    # Feature importance by gain
    if hasattr(model, "get_booster"):
        importance = model.get_booster().get_score(importance_type="gain")
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        metrics["feature_importance_top20"] = dict(sorted_importance[:TOP_N_FEATURES])
    elif hasattr(model, "feature_importances_"):
        feature_names = (
            list(model.feature_names_in_)
            if hasattr(model, "feature_names_in_")
            else [f"f{i}" for i in range(len(model.feature_importances_))]
        )
        pairs = sorted(
            zip(feature_names, model.feature_importances_, strict=True),
            key=lambda x: x[1],
            reverse=True,
        )
        metrics["feature_importance_top20"] = dict(pairs[:TOP_N_FEATURES])

    logger.info(
        "Evaluation: MAE=%.2f, RMSE=%.2f, R²=%.4f, MAPE=%.2f%%",
        metrics["mae"],
        metrics["rmse"],
        metrics["r2"],
        metrics["mape"],
    )

    # Segmented metrics by census tract (or other segment column)
    if segment_values is not None and len(segment_values) == len(y_true_arr):
        seg_metrics: dict[str, dict[str, float]] = {}
        for seg_val in segment_values.dropna().unique():
            mask = (segment_values == seg_val).values
            if mask.sum() < 2:
                continue
            seg_y_true = y_true_arr[mask]
            seg_y_pred = y_pred_arr[mask]
            seg_mae = float(mean_absolute_error(seg_y_true, seg_y_pred))
            seg_mape = _mean_absolute_percentage_error(seg_y_true, seg_y_pred)
            seg_metrics[str(seg_val)] = {"mae": seg_mae, "mape": seg_mape, "n": int(mask.sum())}

        if seg_metrics:
            metrics["segment_metrics"] = seg_metrics
            # Log top/bottom 5 tracts by MAE
            sorted_segs = sorted(seg_metrics.items(), key=lambda x: x[1]["mae"], reverse=True)
            top5 = sorted_segs[:5]
            logger.info("Worst 5 segments by MAE: %s", [(s, m["mae"]) for s, m in top5])

    # Heteroskedasticity diagnostic: Spearman rank correlation between |residuals| and predictions
    abs_residuals = np.abs(y_true_arr - y_pred_arr)
    if len(abs_residuals) >= 3:
        rho, pval = spearmanr(abs_residuals, y_pred_arr)
        metrics["heteroskedasticity_spearman_rho"] = float(rho)
        metrics["heteroskedasticity_spearman_pval"] = float(pval)
        logger.info(
            "Heteroskedasticity diagnostic: Spearman rho=%.4f (p=%.4g)",
            rho,
            pval,
        )

    # Price-tier segmented metrics (quartile-based)
    if len(y_true_arr) >= 4:
        quartile_edges = np.percentile(y_true_arr, [0, 25, 50, 75, 100])
        tier_labels = ["Q1_bottom_25", "Q2_25_50", "Q3_50_75", "Q4_top_25"]
        tier_indices = np.digitize(y_true_arr, quartile_edges[1:-1], right=True)

        price_tier_metrics: dict[str, dict[str, float]] = {}
        for tier_idx, tier_label in enumerate(tier_labels):
            mask = tier_indices == tier_idx
            if mask.sum() < 2:
                continue
            tier_true = y_true_arr[mask]
            tier_pred = y_pred_arr[mask]
            tier_mae = float(mean_absolute_error(tier_true, tier_pred))
            tier_mape = _mean_absolute_percentage_error(tier_true, tier_pred)
            tier_rmse = float(np.sqrt(mean_squared_error(tier_true, tier_pred)))
            tier_median_ae = float(median_absolute_error(tier_true, tier_pred))
            price_tier_metrics[tier_label] = {
                "mae": tier_mae,
                "mape": tier_mape,
                "rmse": tier_rmse,
                "median_ae": tier_median_ae,
                "n": int(mask.sum()),
            }

        if price_tier_metrics:
            metrics["price_tier_metrics"] = price_tier_metrics
            # Flatten for MLflow scalar logging
            for tier_label, tier_m in price_tier_metrics.items():
                for metric_name, metric_val in tier_m.items():
                    metrics[f"tier_{tier_label}_{metric_name}"] = metric_val

    # Attach arrays for downstream plot generation (filtered out by registry scalar check)
    metrics["_y_true"] = y_true_arr
    metrics["_y_pred"] = y_pred_arr
    metrics["_x_test"] = x_test

    return metrics
