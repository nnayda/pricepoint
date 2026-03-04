"""Bayesian hyperparameter tuning for XGBoost via Optuna."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

from pricepoint.models.training import EARLY_STOPPING_ROUNDS, prepare_features

logger = logging.getLogger(__name__)

# Parameters that are fixed (not tuned)
FIXED_PARAMS: dict[str, Any] = {
    "random_state": 42,
    "n_jobs": -1,
    "enable_categorical": True,
    "tree_method": "hist",
}


@dataclass
class TuningResult:
    """Result of a hyperparameter tuning run."""

    best_params: dict[str, Any]
    best_score: float
    n_trials: int
    all_trials: list[dict[str, Any]] = field(default_factory=list)


def _suggest_params(trial: Any) -> dict[str, Any]:
    """Define the Optuna search space for XGBoost hyperparameters."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 200, 1500, step=100),
        "max_depth": trial.suggest_int("max_depth", 3, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 0.8),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 0.7),
        "min_child_weight": trial.suggest_int("min_child_weight", 3, 10),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.1, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1.0, 10.0, log=True),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
    }


def tune_hyperparameters(
    *,
    features: pd.DataFrame,
    target_col: str = "sold_price",
    n_trials: int = 50,
    timeout: int | None = 3600,
    n_cv_folds: int = 3,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    log_to_mlflow: bool = True,
) -> TuningResult:
    """Run Bayesian hyperparameter optimization using Optuna.

    Parameters
    ----------
    features : pd.DataFrame
        Feature matrix including the target column.
    target_col : str
        Name of the target column.
    n_trials : int
        Maximum number of Optuna trials.
    timeout : int | None
        Maximum time in seconds for the study. None means no limit.
    n_cv_folds : int
        Number of cross-validation folds per trial.
    early_stopping_rounds : int
        Early stopping rounds for XGBoost within each fold.
    log_to_mlflow : bool
        Whether to log each trial as a nested MLflow run.

    Returns
    -------
    TuningResult
        Best parameters, best score, and trial summaries.
    """
    import optuna

    x, y = prepare_features(features, target_col)

    kf = KFold(n_splits=n_cv_folds, shuffle=True, random_state=42)
    fold_splits = list(kf.split(x))

    mlflow_parent_run = None
    if log_to_mlflow:
        try:
            import mlflow

            mlflow_parent_run = mlflow.start_run(run_name="hyperparameter_tuning")
        except Exception:
            logger.warning("Failed to start MLflow parent run; continuing without MLflow")
            log_to_mlflow = False

    def objective(trial: optuna.Trial) -> float:
        params = {**FIXED_PARAMS, **_suggest_params(trial)}

        mlflow_child_run = None
        if log_to_mlflow:
            try:
                import mlflow

                mlflow_child_run = mlflow.start_run(run_name=f"trial_{trial.number}", nested=True)
                mlflow.log_params(params)
            except Exception:
                logger.debug("MLflow logging failed for trial %d", trial.number)

        mae_scores: list[float] = []
        try:
            for fold_idx, (train_idx, val_idx) in enumerate(fold_splits):
                x_train, x_val = x.iloc[train_idx], x.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

                model = XGBRegressor(
                    early_stopping_rounds=early_stopping_rounds,
                    **params,
                )
                model.fit(
                    x_train,
                    y_train,
                    eval_set=[(x_val, y_val)],
                    verbose=False,
                )

                y_pred = model.predict(x_val)
                fold_mae = float(np.mean(np.abs(y_val - y_pred)))
                mae_scores.append(fold_mae)

                # Report intermediate value for pruning
                trial.report(float(np.mean(mae_scores)), fold_idx)
                if trial.should_prune():
                    raise optuna.TrialPruned()

            mean_mae = float(np.mean(mae_scores))

            if log_to_mlflow and mlflow_child_run is not None:
                try:
                    import mlflow

                    mlflow.log_metric("cv_mae", mean_mae)
                except Exception:
                    pass

            return mean_mae
        finally:
            if mlflow_child_run is not None:
                try:
                    import mlflow

                    mlflow.end_run()
                except Exception:
                    pass

    sampler = optuna.samplers.TPESampler(seed=42)
    pruner = optuna.pruners.MedianPruner()
    study = optuna.create_study(direction="minimize", sampler=sampler, pruner=pruner)

    logger.info(
        "Starting hyperparameter tuning: n_trials=%d, timeout=%s, cv_folds=%d",
        n_trials,
        timeout,
        n_cv_folds,
    )

    study.optimize(objective, n_trials=n_trials, timeout=timeout)

    if log_to_mlflow and mlflow_parent_run is not None:
        try:
            import mlflow

            mlflow.log_params(study.best_params)
            mlflow.log_metric("best_cv_mae", study.best_value)
            mlflow.log_metric("n_trials_completed", len(study.trials))
            mlflow.end_run()
        except Exception:
            logger.warning("Failed to log final tuning results to MLflow")

    all_trials = [
        {
            "number": t.number,
            "value": t.value,
            "params": t.params,
            "state": str(t.state),
        }
        for t in study.trials
    ]

    best_params = {**FIXED_PARAMS, **study.best_params}

    logger.info(
        "Tuning complete: best MAE=%.2f after %d trials",
        study.best_value,
        len(study.trials),
    )

    return TuningResult(
        best_params=best_params,
        best_score=study.best_value,
        n_trials=len(study.trials),
        all_trials=all_trials,
    )
