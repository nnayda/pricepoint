"""Batch inference pipeline.

Loads the production model from MLflow and scores all properties,
writing predictions back to the property_valuations table.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from pricepoint.db.models import PropertyValuation
from pricepoint.features.assembly import assemble_features
from pricepoint.models.registry import MODEL_NAME

logger = logging.getLogger(__name__)


class ModelInfo(NamedTuple):
    """Loaded model with its registry metadata."""

    model: Any
    version: str
    run_id: str


def load_production_model(
    *, model_name: str = MODEL_NAME, alias: str = "champion"
) -> ModelInfo | None:
    """Load the champion model from MLflow registry.

    Parameters
    ----------
    model_name : str
        Registered model name in MLflow.
    alias : str
        Model alias to load (default: 'champion').

    Returns
    -------
    ModelInfo | None
        The loaded model with version/run metadata, or ``None`` if no
        champion model exists.
    """
    try:
        import mlflow
        import mlflow.sklearn
    except ImportError as exc:
        msg = "mlflow is required for model inference. Install with: pip install mlflow"
        raise ImportError(msg) from exc

    client = mlflow.tracking.MlflowClient()

    try:
        version = client.get_model_version_by_alias(model_name, alias)
    except mlflow.exceptions.MlflowException:
        logger.warning("No '%s' model found for '%s'", alias, model_name)
        return None

    model_uri = f"models:/{model_name}@{alias}"
    logger.info("Loading model '%s' version %s from %s", model_name, version.version, model_uri)

    model = mlflow.sklearn.load_model(model_uri)
    return ModelInfo(model=model, version=version.version, run_id=version.run_id)


def get_model_metrics(run_id: str) -> dict[str, float]:
    """Fetch logged metrics from an MLflow run.

    Parameters
    ----------
    run_id : str
        MLflow run ID associated with the model version.

    Returns
    -------
    dict[str, float]
        Metric name to value mapping (e.g. mae, rmse, mape, r2).
    """
    import mlflow

    client = mlflow.tracking.MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.metrics)


def compute_confidence_interval(
    predicted_value: float, metrics: dict[str, float]
) -> tuple[float, float]:
    """Derive a confidence interval from model performance metrics.

    Strategy:
    1. **Primary** — use MAPE (percentage error scales with value).
    2. **Fallback** — use RMSE as a fixed-dollar margin.
    3. **Last resort** — 10 % of predicted value.

    Parameters
    ----------
    predicted_value : float
        The point prediction for a single property.
    metrics : dict[str, float]
        Model metrics keyed by name (from ``get_model_metrics``).

    Returns
    -------
    tuple[float, float]
        ``(confidence_low, confidence_high)``
    """
    if "mape" in metrics:
        margin = predicted_value * (metrics["mape"] / 100.0)
    elif "rmse" in metrics:
        margin = metrics["rmse"]
    else:
        margin = predicted_value * 0.10

    return (predicted_value - margin, predicted_value + margin)


def predict_batch(model: Any, features_df: pd.DataFrame) -> np.ndarray:
    """Run predictions on a feature DataFrame.

    Parameters
    ----------
    model : fitted model
        A model with a ``predict`` method.
    features_df : pd.DataFrame
        Feature matrix (numeric columns only).

    Returns
    -------
    np.ndarray
        Predicted values, one per row.
    """
    # Keep only numeric columns
    numeric_df = features_df.select_dtypes(include="number")

    # Align columns to model's expected features to avoid mismatch errors
    # when the feature pipeline has added/removed columns since training.
    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        expected = list(expected_features)
        extra = set(numeric_df.columns) - set(expected)
        missing = set(expected) - set(numeric_df.columns)
        if extra:
            logger.warning(
                "Dropping %d features not in trained model: %s", len(extra), sorted(extra)
            )
        if missing:
            logger.warning("Adding %d missing features as NaN: %s", len(missing), sorted(missing))
        numeric_df = numeric_df.reindex(columns=expected, fill_value=np.nan)

    predictions = model.predict(numeric_df)
    logger.info("Generated %d predictions", len(predictions))
    return np.asarray(predictions)


def score_all_properties(db: Session) -> int:
    """Score all properties with the production model.

    Loads the production model, assembles features for all properties
    with a location, generates predictions, and upserts them into
    property_valuations with source='ml_model'.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session.

    Returns
    -------
    int
        Number of properties scored.
    """
    info = load_production_model()
    if info is None:
        logger.warning("No production model available; skipping batch scoring")
        return 0

    model, model_version, run_id = info

    # Fetch model performance metrics for confidence intervals
    try:
        metrics = get_model_metrics(run_id)
    except Exception:
        logger.warning("Could not fetch model metrics for run %s; using defaults", run_id)
        metrics = {}

    # Get IDs of properties with a location
    rows = db.execute(text("SELECT id FROM redfin_listings WHERE location IS NOT NULL")).fetchall()
    property_ids = [r[0] for r in rows]

    if not property_ids:
        logger.warning("No properties with location found; skipping batch scoring")
        return 0

    logger.info("Assembling features for %d properties", len(property_ids))
    features = assemble_features(db, property_ids=property_ids)

    if features.empty:
        logger.warning("Feature matrix is empty; skipping batch scoring")
        return 0

    # Drop target column if present
    if "sold_price" in features.columns:
        features = features.drop(columns=["sold_price"])

    predictions = predict_batch(model, features)

    # Upsert predictions into property_valuations
    now = datetime.now(tz=UTC)
    scored_ids = features.index.tolist()

    for prop_id, pred_value in zip(scored_ids, predictions, strict=True):
        pred_float = float(pred_value)
        ci_low, ci_high = compute_confidence_interval(pred_float, metrics)

        existing = (
            db.query(PropertyValuation)
            .filter(
                PropertyValuation.property_id == int(prop_id),
                PropertyValuation.source == "ml_model",
            )
            .first()
        )

        if existing:
            existing.value = pred_float
            existing.estimated_at = now
            existing.model_version = model_version
            existing.confidence_low = ci_low
            existing.confidence_high = ci_high
        else:
            valuation = PropertyValuation(
                property_id=int(prop_id),
                source="ml_model",
                value=pred_float,
                estimated_at=now,
                model_version=model_version,
                confidence_low=ci_low,
                confidence_high=ci_high,
            )
            db.add(valuation)

    db.commit()
    logger.info("Scored %d properties", len(scored_ids))
    return len(scored_ids)
