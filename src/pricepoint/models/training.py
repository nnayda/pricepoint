"""Model training pipeline.

Trains a home-value forecasting model on the assembled feature matrix.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split
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
MAX_NAN_FRACTION = 0.95
OUTLIER_PERCENTILE_LOW = 0.01
OUTLIER_PERCENTILE_HIGH = 0.99

# Columns that exist in the training matrix for grouping/metadata but are
# not model features.  Dropped before fitting.
TRAINING_METADATA_COLUMNS: list[str] = [
    "property_id",
    "sale_event_id",
    "sale_date",
]

# Features where NULL encodes a real-world state (not just "missing data").
# Missingness indicators let XGBoost learn from presence/absence explicitly.
STRUCTURAL_NULL_FEATURES: list[str] = [
    "association_fee",  # NULL = no HOA
    "years_since_renovation",  # NULL = never renovated
    "years_since_last_sale",  # NULL = no prior sale on record
    "decayed_sale_signal",  # NULL = no prior sale on record
    "num_parking_spaces",  # NULL = not reported (older/smaller homes)
    "appliances_included_count",  # NULL = not reported
    "llm_description_score",  # NULL = no LLM analysis run
    "llm_photo_score",  # NULL = no LLM analysis run
    "comp_median_ppsf",  # NULL = no comps found
    "comp_mean_adjusted_price",  # NULL = no comps found
    "comp_nearest_price",  # NULL = no comps found
    "comp_ppsf_ratio",  # NULL = no comps or no subject ppsf
]


def add_missingness_indicators(x: pd.DataFrame) -> pd.DataFrame:
    """Add binary indicator columns for structurally-null features.

    For each column in ``STRUCTURAL_NULL_FEATURES`` present in *x* whose
    NaN fraction is between 1% and ``MAX_NAN_FRACTION``, creates a new
    ``{col}_missing`` column (int 0/1).  This lets XGBoost learn from
    both presence/absence AND the actual value when present.
    """
    x = x.copy()
    for col in STRUCTURAL_NULL_FEATURES:
        if col not in x.columns:
            continue
        nan_frac = x[col].isna().mean()
        if 0.01 < nan_frac < MAX_NAN_FRACTION:
            x[f"{col}_missing"] = x[col].isna().astype(int)
    return x


def prepare_features(
    features: pd.DataFrame,
    target_col: str,
    *,
    log_transform_target: bool = False,
    filter_outliers: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separate target from features and clean the data.

    Drops columns that are >95% NaN and non-numeric columns.
    Adds missingness indicators for structurally-null features.
    Optionally filters target outliers and applies log-transform.
    Returns (X, y).
    """
    if target_col not in features.columns:
        msg = f"Target column '{target_col}' not found in DataFrame"
        raise ValueError(msg)

    y = features[target_col].copy()
    x = features.drop(columns=[target_col])

    # Strip training metadata columns (property_id, sale_event_id, sale_date)
    # but preserve is_historical and record_age_years as real features
    meta_to_drop = [c for c in TRAINING_METADATA_COLUMNS if c in x.columns]
    if meta_to_drop:
        logger.info("Dropping training metadata columns: %s", meta_to_drop)
        x = x.drop(columns=meta_to_drop)

    # Coerce object columns to numeric where possible (e.g. all-None columns
    # loaded from JSONB that pandas inferred as object instead of float)
    from pricepoint.features.housing import CATEGORICAL_COLUMNS

    for col in x.select_dtypes(include=["object"]).columns:
        if col not in CATEGORICAL_COLUMNS:
            x[col] = pd.to_numeric(x[col], errors="coerce")

    # Keep numeric, boolean, and category columns; drop everything else
    kept_cols = x.select_dtypes(include=["number", "bool", "category"]).columns.tolist()
    dropped = set(x.columns) - set(kept_cols)
    if dropped:
        logger.info("Dropping non-numeric/non-category columns: %s", dropped)
    x = x[kept_cols]

    # Ensure known categorical columns have category dtype
    for col in CATEGORICAL_COLUMNS:
        if col in x.columns:
            x[col] = x[col].astype("category")

    # Add missingness indicators for structurally-null features
    x = add_missingness_indicators(x)

    # Drop columns with >95% NaN
    nan_fractions = x.isna().mean()
    high_nan_cols = nan_fractions[nan_fractions > MAX_NAN_FRACTION].index.tolist()
    if high_nan_cols:
        logger.info("Dropping columns with >95%% NaN: %s", high_nan_cols)
        x = x.drop(columns=high_nan_cols)

    # Log retained columns with notable NaN fractions for monitoring
    nan_fractions = x.isna().mean()
    notable_nan = nan_fractions[(nan_fractions > 0.2) & (nan_fractions <= MAX_NAN_FRACTION)]
    if not notable_nan.empty:
        logger.info(
            "Retained %d columns with 20-95%% NaN: %s",
            len(notable_nan),
            dict(notable_nan.round(2)),
        )

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
    # Extract grouping column before prepare_features drops it
    groups = None
    if "property_id" in features.columns:
        groups = features.loc[features[target_col].notna(), "property_id"]

    x, y = prepare_features(features, target_col, log_transform_target=log_transform_target)

    # Correlation-based feature selection
    from pricepoint.models.selection import select_features

    x = select_features(x)

    # Align groups with the cleaned X/y (rows may have been dropped)
    if groups is not None:
        groups = groups.reindex(x.index)

    # Use GroupShuffleSplit when multi-sale records are present to prevent
    # the same property appearing in both train and test sets
    if groups is not None:
        gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=42)
        train_idx, test_idx = next(gss.split(x, y, groups=groups))
        x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        logger.info(
            "Using GroupShuffleSplit: %d unique properties in train, %d in test",
            groups.iloc[train_idx].nunique(),
            groups.iloc[test_idx].nunique(),
        )
    else:
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=TEST_SIZE, random_state=42
        )

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
