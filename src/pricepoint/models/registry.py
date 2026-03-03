"""MLflow model registry integration.

Handles logging models, metrics, and artifacts to MLflow, and promoting
models through staging/production lifecycle stages.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_NAME = "pricepoint-home-value"


def log_model(
    *,
    model: Any,
    metrics: dict[str, Any],
    run_name: str | None = None,
    model_name: str = MODEL_NAME,
    input_example: pd.DataFrame | None = None,
    generate_plots: bool = True,
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

    # Extract CV metrics for fold comparison plot
    cv_metrics: dict[str, Any] = {
        k: v for k, v in metrics.items()
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
                        output_dir=Path(tmpdir),
                    )
                    for plot_path in plot_paths:
                        mlflow.log_artifact(str(plot_path), artifact_path="plots")
                    logger.info("Logged %d evaluation plots", len(plot_paths))
            except Exception:
                logger.warning("Failed to generate evaluation plots", exc_info=True)

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
