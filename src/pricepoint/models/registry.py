"""MLflow model registry integration.

Handles logging models, metrics, and artifacts to MLflow, and promoting
models through staging/production lifecycle stages.
"""

from __future__ import annotations

import contextlib
import dataclasses
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

LOWER_IS_BETTER = {"mae", "rmse", "mape", "median_ae", "mae_mean", "rmse_mean"}

MODEL_NAME = "pricepoint-home-value"


def log_model(
    *,
    model: Any,
    metrics: dict[str, Any],
    run_name: str | None = None,
    model_name: str = MODEL_NAME,
    input_example: pd.DataFrame | None = None,
    generate_plots: bool = True,
    eda_data: tuple[pd.DataFrame, pd.Series] | None = None,
) -> str:
    """Log a trained model and its metrics to MLflow.

    Parameters
    ----------
    model : fitted model
        The trained model to log.
    metrics : dict
        Evaluation metrics to log.
    run_name : str, optional
        Name for the MLflow run.
    model_name : str
        Name for model registration.
    input_example : pd.DataFrame, optional
        A small sample of input data used to infer the model signature.
    generate_plots : bool
        Whether to generate and log evaluation plots as artifacts.
    eda_data : tuple[pd.DataFrame, pd.Series], optional
        (X, y) tuple for generating EDA plots. If provided, EDA plots are
        generated and logged under the ``eda/`` artifact subdirectory.

    Returns
    -------
    str
        The MLflow run ID.
    """
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError as exc:
        msg = "mlflow is required for model registry. Install with: pip install mlflow"
        raise ImportError(msg) from exc

    # Log params from model if available
    params_to_log: dict[str, Any] = {}
    if hasattr(model, "get_params"):
        params_to_log = {k: v for k, v in model.get_params().items() if v is not None}

    # Separate scalar metrics from non-scalar (like feature importance dict)
    scalar_metrics: dict[str, float] = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            scalar_metrics[key] = float(value)

    # Extract prediction arrays for plot generation (not logged as metrics)
    y_true: np.ndarray | None = metrics.get("_y_true")
    y_pred: np.ndarray | None = metrics.get("_y_pred")
    x_test: pd.DataFrame | None = metrics.get("_x_test")
    feature_importance: dict[str, float] | None = metrics.get("feature_importance_top20")
    segment_metrics: dict[str, dict[str, float]] | None = metrics.get("segment_metrics")

    # Extract CV metrics for fold comparison plot
    cv_metrics: dict[str, Any] = {
        k: v
        for k, v in metrics.items()
        if isinstance(v, (int, float)) and any(k.startswith(p) for p in ("mae_", "rmse_", "r2_"))
    }

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params_to_log)
        mlflow.log_metrics(scalar_metrics)

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=model_name,
            input_example=input_example,
        )

        # Generate and log evaluation plots
        if generate_plots and y_true is not None and y_pred is not None:
            try:
                from pricepoint.models.plots import generate_evaluation_plots

                with tempfile.TemporaryDirectory() as tmpdir:
                    plot_paths = generate_evaluation_plots(
                        model=model,
                        y_true=y_true,
                        y_pred=y_pred,
                        feature_importance=feature_importance,
                        cv_metrics=cv_metrics or None,
                        x_test=x_test,
                        segment_metrics=segment_metrics,
                        output_dir=Path(tmpdir),
                    )
                    for plot_path in plot_paths:
                        mlflow.log_artifact(str(plot_path), artifact_path="plots")
                    logger.info("Logged %d evaluation plots", len(plot_paths))
            except Exception:
                logger.warning("Failed to generate evaluation plots", exc_info=True)

        # Generate and log EDA plots
        if eda_data is not None:
            try:
                from pricepoint.models.eda import generate_eda_plots

                eda_x, eda_y = eda_data
                with tempfile.TemporaryDirectory() as eda_tmpdir:
                    eda_paths = generate_eda_plots(
                        eda_x,
                        eda_y,
                        log_transformed=True,
                        output_dir=Path(eda_tmpdir),
                    )
                    for eda_path in eda_paths:
                        mlflow.log_artifact(str(eda_path), artifact_path="eda")
                    logger.info("Logged %d EDA plots", len(eda_paths))
            except Exception:
                logger.warning("Failed to generate EDA plots", exc_info=True)

        run_id = run.info.run_id
        logger.info("Logged model to MLflow run %s", run_id)

    return run_id


def promote_model(
    *,
    model_name: str = MODEL_NAME,
    version: int,
    alias: str = "champion",
) -> None:
    """Set an alias on a registered model version.

    Parameters
    ----------
    model_name : str
        Registered model name.
    version : int
        Model version number.
    alias : str
        Alias to assign (e.g. 'champion', 'challenger').
    """
    try:
        import mlflow
    except ImportError as exc:
        msg = "mlflow is required for model registry. Install with: pip install mlflow"
        raise ImportError(msg) from exc

    client = mlflow.tracking.MlflowClient()
    client.set_registered_model_alias(
        name=model_name,
        alias=alias,
        version=str(version),
    )
    logger.info(
        "Set alias '%s' on model '%s' version %d",
        alias,
        model_name,
        version,
    )


@dataclass
class ComparisonResult:
    """Result of comparing a candidate model against the current champion."""

    promoted: bool
    reason: str
    candidate_version: int
    candidate_run_id: str
    champion_version: int | None = None
    champion_run_id: str | None = None
    candidate_metrics: dict[str, float] = field(default_factory=dict)
    champion_metrics: dict[str, float] = field(default_factory=dict)
    primary_metric: str = "mae"


def _is_candidate_better(
    candidate_val: float,
    champion_val: float,
    metric_name: str,
) -> bool:
    """Return True if the candidate value is better than the champion value.

    Error metrics (MAE, RMSE, etc.) are lower-is-better; R² is higher-is-better.
    """
    if metric_name in LOWER_IS_BETTER:
        return candidate_val < champion_val
    return candidate_val > champion_val


def compare_and_promote(
    *,
    run_id: str,
    model_name: str = MODEL_NAME,
    primary_metric: str = "mae",
    auto_promote: bool = True,
) -> dict[str, Any]:
    """Compare a newly registered model against the current champion.

    Promotes the candidate if it is better on the primary metric, or if no
    champion exists yet.

    Parameters
    ----------
    run_id : str
        MLflow run ID of the candidate model.
    model_name : str
        Registered model name.
    primary_metric : str
        Metric name to compare on (e.g. "mae", "rmse", "r2").
    auto_promote : bool
        Whether to automatically promote a better candidate.

    Returns
    -------
    dict
        Serializable comparison result for Airflow XCom.
    """
    try:
        import mlflow
        from mlflow.exceptions import MlflowException
    except ImportError as exc:
        msg = "mlflow is required for model registry. Install with: pip install mlflow"
        raise ImportError(msg) from exc

    client = mlflow.tracking.MlflowClient()

    # --- Resolve candidate model version ---
    candidate_versions = client.search_model_versions(f"run_id='{run_id}'")
    if not candidate_versions:
        msg = f"No model version found for run_id={run_id}"
        raise ValueError(msg)
    candidate_mv = candidate_versions[0]
    candidate_version = int(candidate_mv.version)

    candidate_metrics = {
        k: v for k, v in client.get_run(run_id).data.metrics.items() if isinstance(v, (int, float))
    }

    # --- Resolve current champion ---
    champion_mv = None
    with contextlib.suppress(MlflowException):
        champion_mv = client.get_model_version_by_alias(model_name, "champion")

    # --- No existing champion → promote ---
    if champion_mv is None:
        result = ComparisonResult(
            promoted=True,
            reason="No existing champion — promoting first model",
            candidate_version=candidate_version,
            candidate_run_id=run_id,
            candidate_metrics=candidate_metrics,
            primary_metric=primary_metric,
        )
        promote_model(model_name=model_name, version=candidate_version)
        logger.info("Promoted v%d as first champion", candidate_version)
        _tag_comparison(client, run_id, result)
        return dataclasses.asdict(result)

    # --- Compare metrics ---
    champion_run_id = champion_mv.run_id
    champion_version = int(champion_mv.version)
    champion_metrics = {
        k: v
        for k, v in client.get_run(champion_run_id).data.metrics.items()
        if isinstance(v, (int, float))
    }

    candidate_val = candidate_metrics.get(primary_metric)
    champion_val = champion_metrics.get(primary_metric)

    if candidate_val is None:
        result = ComparisonResult(
            promoted=False,
            reason=f"Candidate missing primary metric '{primary_metric}'",
            candidate_version=candidate_version,
            candidate_run_id=run_id,
            champion_version=champion_version,
            champion_run_id=champion_run_id,
            candidate_metrics=candidate_metrics,
            champion_metrics=champion_metrics,
            primary_metric=primary_metric,
        )
        _tag_comparison(client, run_id, result)
        return dataclasses.asdict(result)

    if champion_val is None or _is_candidate_better(candidate_val, champion_val, primary_metric):
        if auto_promote:
            result = ComparisonResult(
                promoted=True,
                reason=(
                    f"Candidate {primary_metric}={candidate_val:.4f} beats "
                    f"champion {primary_metric}={champion_val}"
                ),
                candidate_version=candidate_version,
                candidate_run_id=run_id,
                champion_version=champion_version,
                champion_run_id=champion_run_id,
                candidate_metrics=candidate_metrics,
                champion_metrics=champion_metrics,
                primary_metric=primary_metric,
            )
            promote_model(model_name=model_name, version=candidate_version)
            logger.info(
                "Promoted v%d over v%d (%s: %.4f → %.4f)",
                candidate_version,
                champion_version,
                primary_metric,
                champion_val if champion_val is not None else float("nan"),
                candidate_val,
            )
        else:
            result = ComparisonResult(
                promoted=False,
                reason=(
                    f"Candidate is better ({primary_metric}={candidate_val:.4f} vs "
                    f"{champion_val}) but auto_promote is disabled"
                ),
                candidate_version=candidate_version,
                candidate_run_id=run_id,
                champion_version=champion_version,
                champion_run_id=champion_run_id,
                candidate_metrics=candidate_metrics,
                champion_metrics=champion_metrics,
                primary_metric=primary_metric,
            )
            logger.info("Candidate v%d is better but auto_promote=False", candidate_version)
    else:
        result = ComparisonResult(
            promoted=False,
            reason=(
                f"Champion v{champion_version} is still better "
                f"({primary_metric}={champion_val:.4f} vs {candidate_val:.4f})"
            ),
            candidate_version=candidate_version,
            candidate_run_id=run_id,
            champion_version=champion_version,
            champion_run_id=champion_run_id,
            candidate_metrics=candidate_metrics,
            champion_metrics=champion_metrics,
            primary_metric=primary_metric,
        )
        logger.info(
            "Champion v%d retained (%s: %.4f vs candidate %.4f)",
            champion_version,
            primary_metric,
            champion_val,
            candidate_val,
        )

    _tag_comparison(client, run_id, result)
    return dataclasses.asdict(result)


def _tag_comparison(
    client: Any,
    run_id: str,
    result: ComparisonResult,
) -> None:
    """Log comparison metadata as tags on the candidate run."""
    client.set_tag(run_id, "promotion.promoted", str(result.promoted))
    client.set_tag(run_id, "promotion.reason", result.reason)
    client.set_tag(run_id, "promotion.primary_metric", result.primary_metric)
    if result.champion_version is not None:
        client.set_tag(run_id, "promotion.champion_version", str(result.champion_version))
