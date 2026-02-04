"""MLflow model registry integration.

Handles logging models, metrics, and artifacts to MLflow, and promoting
models through staging/production lifecycle stages.
"""


def log_model(*, model: object, metrics: dict, run_name: str | None = None) -> str:
    """Log a trained model and its metrics to MLflow.

    Returns the MLflow run ID.
    """
    raise NotImplementedError


def promote_model(*, model_name: str, version: int, stage: str = "Production") -> None:
    """Transition a registered model version to the given stage."""
    raise NotImplementedError
