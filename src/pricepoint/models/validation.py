"""Model validation -- cross-validation and holdout evaluation."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from pricepoint.models.training import DEFAULT_PARAMS, prepare_features

logger = logging.getLogger(__name__)


def cross_validate(
    *,
    features: pd.DataFrame,
    target_col: str = "sold_price",
    n_splits: int = 5,
    params: dict[str, Any] | None = None,
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

    Returns
    -------
    dict
        Mean and std of MAE, RMSE, R² across folds.
    """
    x, y = prepare_features(features, target_col)

    model_params = {**DEFAULT_PARAMS, **(params or {})}
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    mae_scores: list[float] = []
    rmse_scores: list[float] = []
    r2_scores: list[float] = []

    for fold, (train_idx, test_idx) in enumerate(kf.split(x), 1):
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

        mae_scores.append(float(mean_absolute_error(y_test, y_pred)))
        rmse_scores.append(float(np.sqrt(mean_squared_error(y_test, y_pred))))
        r2_scores.append(float(r2_score(y_test, y_pred)))

        logger.info(
            "Fold %d/%d: MAE=%.2f, RMSE=%.2f, R²=%.4f",
            fold,
            n_splits,
            mae_scores[-1],
            rmse_scores[-1],
            r2_scores[-1],
        )

    return {
        "mae_mean": float(np.mean(mae_scores)),
        "mae_std": float(np.std(mae_scores)),
        "rmse_mean": float(np.mean(rmse_scores)),
        "rmse_std": float(np.std(rmse_scores)),
        "r2_mean": float(np.mean(r2_scores)),
        "r2_std": float(np.std(r2_scores)),
    }
