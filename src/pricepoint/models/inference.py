"""Batch inference pipeline.

Loads the production model from MLflow and scores all properties,
writing predictions back to the property_valuations table.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from pricepoint.db.models import PropertyValuation
from pricepoint.features.assembly import assemble_features
from pricepoint.models.registry import MODEL_NAME

logger = logging.getLogger(__name__)


def load_production_model(*, model_name: str = MODEL_NAME) -> Any:
    """Load the Production-stage model from MLflow registry.

    Parameters
    ----------
    model_name : str
        Registered model name in MLflow.

    Returns
    -------
    model
        The loaded model object, or ``None`` if no Production model exists.
    """
    try:
        import mlflow
        import mlflow.xgboost
    except ImportError as exc:
        msg = "mlflow is required for model inference. Install with: pip install mlflow"
        raise ImportError(msg) from exc

    client = mlflow.tracking.MlflowClient()

    # Find the latest Production version
    versions = client.get_latest_versions(model_name, stages=["Production"])
    if not versions:
        logger.warning("No Production model found for '%s'", model_name)
        return None

    version = versions[0]
    model_uri = f"models:/{model_name}/{version.version}"
    logger.info("Loading model '%s' version %s from %s", model_name, version.version, model_uri)

    model = mlflow.xgboost.load_model(model_uri)
    return model


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
    model = load_production_model()
    if model is None:
        logger.warning("No production model available; skipping batch scoring")
        return 0

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
        existing = (
            db.query(PropertyValuation)
            .filter(
                PropertyValuation.property_id == int(prop_id),
                PropertyValuation.source == "ml_model",
            )
            .first()
        )

        if existing:
            existing.value = float(pred_value)
            existing.estimated_at = now
        else:
            valuation = PropertyValuation(
                property_id=int(prop_id),
                source="ml_model",
                value=float(pred_value),
                estimated_at=now,
            )
            db.add(valuation)

    db.commit()
    logger.info("Scored %d properties", len(scored_ids))
    return len(scored_ids)
