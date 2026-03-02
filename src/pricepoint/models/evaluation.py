"""Model evaluation -- compute metrics on held-out test data."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
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

    return metrics
