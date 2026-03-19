"""Model validation -- cross-validation and holdout evaluation."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold
from xgboost import XGBRegressor

from pricepoint.models.training import DEFAULT_PARAMS, prepare_features

logger = logging.getLogger(__name__)


def cross_validate(
    *,
    features: pd.DataFrame,
    target_col: str = "sold_price",
    n_splits: int = 5,
    params: dict[str, Any] | None = None,
    log_transform_target: bool = True,
    temporal: bool = False,
) -> dict[str, float]:
    """Run k-fold cross-validation and return aggregated metrics.

    Parameters
    ----------
    features : pd.DataFrame
        Feature matrix including the target column.
    target_col : str
        Name of the target column.
    n_splits : int
        Number of folds.
    params : dict, optional
        Override default XGBoost hyperparameters.
    log_transform_target : bool
        Apply ``log1p`` to the target variable before training.
    temporal : bool
        If True, sort by ``sold_date`` (if present) and use
        ``TimeSeriesSplit`` instead of ``KFold``.  Metrics are still
        computed in dollar-space when ``log_transform_target=True``.

    Returns
    -------
    dict
        Mean and std of MAE, RMSE, R² across folds, plus
        ``importance_stability`` (mean Spearman rho of feature importance
        rankings across fold pairs).
    """
    from scipy.stats import spearmanr
    from sklearn.model_selection import TimeSeriesSplit

    # Extract grouping column before prepare_features drops it
    groups = None
    if "property_id" in features.columns:
        groups = features.loc[features[target_col].notna(), "property_id"]

    x, y = prepare_features(features, target_col, log_transform_target=log_transform_target)

    # For temporal CV, sort by sold_date then drop it
    if temporal and "sold_date" in x.columns:
        sort_order = x["sold_date"].argsort()
        x = x.iloc[sort_order]
        y = y.iloc[sort_order]
        x = x.drop(columns=["sold_date"])
    elif "sold_date" in x.columns:
        x = x.drop(columns=["sold_date"])

    # Align groups with the cleaned X/y (rows may have been dropped)
    if groups is not None:
        groups = groups.reindex(x.index)

    model_params = {**DEFAULT_PARAMS, **(params or {})}

    # Use GroupKFold when multi-sale records are present to prevent
    # the same property appearing in different folds
    if groups is not None and not temporal:
        splitter: KFold | TimeSeriesSplit | GroupKFold = GroupKFold(n_splits=n_splits)
    elif temporal:
        splitter = TimeSeriesSplit(n_splits=n_splits)
    else:
        splitter = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    mae_scores: list[float] = []
    rmse_scores: list[float] = []
    r2_scores: list[float] = []
    fold_importances: list[np.ndarray] = []

    split_args = (x,) if groups is None else (x, y, groups)
    for fold, (train_idx, test_idx) in enumerate(splitter.split(*split_args), 1):
        x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = XGBRegressor(**model_params)
        model.fit(
            x_train,
            y_train,
            eval_set=[(x_test, y_test)],
            verbose=False,
        )

        y_pred = model.predict(x_test)

        # Convert back to dollar-space for metrics if log-transformed
        if log_transform_target:
            y_pred_dollar = np.expm1(y_pred)
            y_test_dollar = np.expm1(y_test)
        else:
            y_pred_dollar = y_pred
            y_test_dollar = y_test

        mae_scores.append(float(mean_absolute_error(y_test_dollar, y_pred_dollar)))
        rmse_scores.append(float(np.sqrt(mean_squared_error(y_test_dollar, y_pred_dollar))))
        r2_scores.append(float(r2_score(y_test_dollar, y_pred_dollar)))

        # Collect feature importances for stability check
        if hasattr(model, "feature_importances_"):
            fold_importances.append(model.feature_importances_)

        logger.info(
            "Fold %d/%d: MAE=%.2f, RMSE=%.2f, R²=%.4f",
            fold,
            n_splits,
            mae_scores[-1],
            rmse_scores[-1],
            r2_scores[-1],
        )

    result: dict[str, float] = {
        "mae_mean": float(np.mean(mae_scores)),
        "mae_std": float(np.std(mae_scores)),
        "rmse_mean": float(np.mean(rmse_scores)),
        "rmse_std": float(np.std(rmse_scores)),
        "r2_mean": float(np.mean(r2_scores)),
        "r2_std": float(np.std(r2_scores)),
    }

    # Feature importance stability: mean Spearman rho across fold pairs
    if len(fold_importances) >= 2:
        rhos: list[float] = []
        for i in range(len(fold_importances)):
            for j in range(i + 1, len(fold_importances)):
                rho, _ = spearmanr(fold_importances[i], fold_importances[j])
                rhos.append(float(rho))
        result["importance_stability"] = float(np.mean(rhos))

    return result
