"""Model training pipeline.

Trains a home-value forecasting model on the assembled feature matrix.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

# Default XGBoost hyperparameters
DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 500,
    "max_depth": 4,
    "learning_rate": 0.03,
    "subsample": 0.7,
    "colsample_bytree": 0.5,
    "min_child_weight": 5,
    "reg_alpha": 0.3,
    "reg_lambda": 3.0,
    "gamma": 0.1,
    "random_state": 42,
    "n_jobs": -1,
    "enable_categorical": True,
    "tree_method": "hist",
}

EARLY_STOPPING_ROUNDS = 50
TEST_SIZE = 0.2
MAX_NAN_FRACTION = 0.5
OUTLIER_PERCENTILE_LOW = 0.01
OUTLIER_PERCENTILE_HIGH = 0.99


def prepare_features(
    features: pd.DataFrame,
    target_col: str,
    *,
    log_transform_target: bool = False,
    filter_outliers: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separate target from features and clean the data.

    Drops columns that are >50% NaN and non-numeric columns.
    Optionally filters target outliers and applies log-transform.
    Returns (X, y).
    """
    if target_col not in features.columns:
        msg = f"Target column '{target_col}' not found in DataFrame"
        raise ValueError(msg)

    y = features[target_col].copy()
    x = features.drop(columns=[target_col])

    # Keep numeric and category columns; drop everything else
    from pricepoint.features.housing import CATEGORICAL_COLUMNS

    kept_cols = x.select_dtypes(include=["number", "category"]).columns.tolist()
    dropped = set(x.columns) - set(kept_cols)
    if dropped:
        logger.info("Dropping non-numeric/non-category columns: %s", dropped)
    x = x[kept_cols]

    # Ensure known categorical columns have category dtype
    for col in CATEGORICAL_COLUMNS:
        if col in x.columns:
            x[col] = x[col].astype("category")

    # Drop columns with >50% NaN
    nan_fractions = x.isna().mean()
    high_nan_cols = nan_fractions[nan_fractions > MAX_NAN_FRACTION].index.tolist()
    if high_nan_cols:
        logger.info("Dropping columns with >50%% NaN: %s", high_nan_cols)
        x = x.drop(columns=high_nan_cols)

    # Drop rows where target is NaN
    valid_mask = y.notna()
    if not valid_mask.all():
        logger.info("Dropping %d rows with NaN target", (~valid_mask).sum())
        x = x.loc[valid_mask]
        y = y.loc[valid_mask]

    # Filter target outliers (e.g. $1 family transfers, $10M+ properties)
    if filter_outliers and len(y) > 0:
        low = float(np.percentile(y, OUTLIER_PERCENTILE_LOW * 100))
        high = float(np.percentile(y, OUTLIER_PERCENTILE_HIGH * 100))
        outlier_mask = (y >= low) & (y <= high)
        n_outliers = (~outlier_mask).sum()
        if n_outliers > 0:
            logger.info(
                "Filtering %d target outliers outside [%.0f, %.0f]",
                n_outliers,
                low,
                high,
            )
            x = x.loc[outlier_mask]
            y = y.loc[outlier_mask]

    if x.empty:
        msg = "No features remaining after cleaning"
        raise ValueError(msg)

    # Log-transform target for more symmetric residuals
    if log_transform_target:
        y = np.log1p(y)

    return x, y


def train_model(
    *,
    features: pd.DataFrame,
    target_col: str = "sold_price",
    params: dict[str, Any] | None = None,
    log_transform_target: bool = True,
) -> tuple[XGBRegressor, list[int]]:
    """Train an XGBoost model on the given feature matrix.

    Parameters
    ----------
    features : pd.DataFrame
        Feature matrix including the target column.
    target_col : str
        Name of the target column.
    params : dict, optional
        Override default hyperparameters.
    log_transform_target : bool
        Apply ``log1p`` to the target variable before training.

    Returns
    -------
    tuple[XGBRegressor, list[int]]
        The fitted model and the index values of the held-out test set
        (used downstream to evaluate on unseen data only).
    """
    x, y = prepare_features(features, target_col, log_transform_target=log_transform_target)

    # Correlation-based feature selection
    from pricepoint.models.selection import select_features

    x = select_features(x)

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=TEST_SIZE, random_state=42)

    model_params = {**DEFAULT_PARAMS, **(params or {})}
    model = XGBRegressor(
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        **model_params,
    )

    logger.info(
        "Training XGBoost with %d samples (%d train, %d test), %d features",
        len(x),
        len(x_train),
        len(x_test),
        x.shape[1],
    )

    model.fit(
        x_train,
        y_train,
        eval_set=[(x_test, y_test)],
        verbose=False,
    )

    # Store log-transform flag as model attribute for downstream use
    model.log_target = log_transform_target  # type: ignore[attr-defined]

    # Compute calibration residuals on test set for conformal prediction intervals
    y_pred_test = model.predict(x_test)
    if log_transform_target:
        cal_residuals = np.expm1(y_test.values) - np.expm1(y_pred_test)
    else:
        cal_residuals = y_test.values - y_pred_test
    model.calibration_residuals_ = np.sort(np.abs(cal_residuals))  # type: ignore[attr-defined]

    # Normalized calibration residuals for price-adaptive conformal intervals
    cal_predicted = np.expm1(y_pred_test) if log_transform_target else y_pred_test
    nonzero_mask = np.abs(cal_predicted) > 0
    if nonzero_mask.any():
        normalized = np.abs(cal_residuals[nonzero_mask]) / np.abs(cal_predicted[nonzero_mask])
        model.calibration_residuals_normalized_ = np.sort(normalized)  # type: ignore[attr-defined]
    else:
        model.calibration_residuals_normalized_ = np.array([], dtype=np.float64)  # type: ignore[attr-defined]

    try:
        best_iter = model.best_iteration
    except AttributeError:
        best_iter = model_params.get("n_estimators", "N/A")
    logger.info("Training complete. Best iteration: %s", best_iter)

    test_indices = x_test.index.tolist()
    return model, test_indices
