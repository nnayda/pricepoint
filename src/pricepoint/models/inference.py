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

from pricepoint.db.models import PropertyShapValue, PropertyValuation
from pricepoint.features.assembly import assemble_features
from pricepoint.features.store import load_feature_matrix
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
    predicted_value: float,
    metrics: dict[str, float],
    calibration_residuals: np.ndarray | None = None,
    confidence_level: float = 0.90,
) -> tuple[float, float]:
    """Derive a confidence interval for a prediction.

    Strategy:
    1. **Primary** — split conformal prediction using calibration residuals.
       The interval width is the α-quantile of sorted absolute residuals
       from a held-out calibration set.  This is distribution-free and
       provides valid marginal coverage.
    2. **Fallback** — use MAPE (percentage error scales with value).
    3. **Fallback** — use RMSE as a fixed-dollar margin.
    4. **Last resort** — 10 % of predicted value.

    Parameters
    ----------
    predicted_value : float
        The point prediction for a single property.
    metrics : dict[str, float]
        Model metrics keyed by name (from ``get_model_metrics``).
    calibration_residuals : np.ndarray | None
        Sorted absolute residuals from a held-out calibration set.
    confidence_level : float
        Desired coverage probability (default 0.90).

    Returns
    -------
    tuple[float, float]
        ``(confidence_low, confidence_high)``
    """
    if calibration_residuals is not None and len(calibration_residuals) > 0:
        # Conformal prediction: quantile of calibration residuals
        q = min(confidence_level, (1 + 1 / len(calibration_residuals)) * confidence_level)
        margin = float(np.quantile(np.abs(calibration_residuals), min(q, 1.0)))
    elif "mape" in metrics:
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
    from pricepoint.features.housing import CATEGORICAL_COLUMNS

    # Keep numeric and category columns
    usable_df = features_df.select_dtypes(include=["number", "category"])

    # Align columns to model's expected features to avoid mismatch errors
    # when the feature pipeline has added/removed columns since training.
    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        expected = list(expected_features)
        extra = set(usable_df.columns) - set(expected)
        missing = set(expected) - set(usable_df.columns)
        if extra:
            logger.warning(
                "Dropping %d features not in trained model: %s", len(extra), sorted(extra)
            )
        if missing:
            logger.warning("Adding %d missing features as NaN: %s", len(missing), sorted(missing))
        usable_df = usable_df.reindex(columns=expected, fill_value=np.nan)

    # Re-cast categorical columns after reindex
    for col in CATEGORICAL_COLUMNS:
        if col in usable_df.columns:
            usable_df[col] = usable_df[col].astype("category")

    predictions = model.predict(usable_df)

    # Inverse log-transform if the model was trained on log1p(target)
    if getattr(model, "log_target", False) is True:
        predictions = np.expm1(predictions)

    logger.info("Generated %d predictions", len(predictions))
    return np.asarray(predictions)


def compute_shap_values(model: Any, features_df: pd.DataFrame) -> list[dict[str, object]]:
    """Compute per-instance SHAP values for a single property.

    Uses ``shap.TreeExplainer`` for tree-based models (XGBoost, LightGBM,
    RandomForest) to produce exact Shapley values.  Each value represents
    the feature's contribution (in prediction units, i.e. dollars) to
    pushing the prediction away from the base value.

    Parameters
    ----------
    model : fitted model
        A tree-based model with a ``predict`` method.
    features_df : pd.DataFrame
        Feature matrix for a single property (one row).

    Returns
    -------
    list[dict[str, object]]
        ``[{"feature": str, "shap_value": float}, ...]`` sorted by
        absolute impact descending.
    """
    from pricepoint.features.housing import CATEGORICAL_COLUMNS

    # Align columns to model's expected features (same logic as predict_batch)
    usable_df = features_df.select_dtypes(include=["number", "category"])
    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        expected = list(expected_features)
        usable_df = usable_df.reindex(columns=expected, fill_value=np.nan)

    # Re-cast categorical columns after reindex
    for col in CATEGORICAL_COLUMNS:
        if col in usable_df.columns:
            usable_df[col] = usable_df[col].astype("category")

    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(usable_df)

    # shap_values shape: (n_samples, n_features) — take first row
    row_values = shap_values[0] if len(shap_values.shape) > 1 else shap_values
    feature_names = list(usable_df.columns)

    results: list[dict[str, object]] = []
    for name, val in zip(feature_names, row_values, strict=True):
        results.append({"feature": name, "shap_value": float(val)})

    # Sort by absolute impact descending
    results.sort(key=lambda x: abs(float(x["shap_value"])), reverse=True)
    return results


def compute_shap_values_batch(
    model: Any, features_df: pd.DataFrame
) -> tuple[list[list[dict[str, object]]], float | None]:
    """Compute SHAP values for an entire batch of properties at once.

    Uses ``shap.TreeExplainer`` which is optimised for batch computation
    via C-level tree traversal.

    Parameters
    ----------
    model : fitted model
        A tree-based model.
    features_df : pd.DataFrame
        Feature matrix for multiple properties (N rows).

    Returns
    -------
    tuple[list[list[dict[str, object]]], float | None]
        ``(per_property_shap_list, base_value)`` — each element is a list
        of ``{"feature": str, "shap_value": float}`` sorted by absolute
        impact descending.  ``base_value`` is the explainer's
        ``expected_value`` (average prediction).
    """
    from pricepoint.features.housing import CATEGORICAL_COLUMNS

    usable_df = features_df.select_dtypes(include=["number", "category"])
    expected_features = getattr(model, "feature_names_in_", None)
    if expected_features is not None:
        expected = list(expected_features)
        usable_df = usable_df.reindex(columns=expected, fill_value=np.nan)

    # Re-cast categorical columns after reindex
    for col in CATEGORICAL_COLUMNS:
        if col in usable_df.columns:
            usable_df[col] = usable_df[col].astype("category")

    import shap

    explainer = shap.TreeExplainer(model)
    shap_matrix = explainer.shap_values(usable_df)  # (n_samples, n_features)

    # Extract base value (expected_value may be scalar or 1-element array)
    raw_ev = getattr(explainer, "expected_value", None)
    if raw_ev is not None:
        base_value = float(raw_ev[0]) if isinstance(raw_ev, np.ndarray) else float(raw_ev)
    else:
        base_value = None

    feature_names = list(usable_df.columns)
    all_results: list[list[dict[str, object]]] = []

    for row_idx in range(len(usable_df)):
        row_values = shap_matrix[row_idx]
        results: list[dict[str, object]] = [
            {"feature": name, "shap_value": float(val)}
            for name, val in zip(feature_names, row_values, strict=True)
        ]
        results.sort(key=lambda x: abs(float(x["shap_value"])), reverse=True)
        all_results.append(results)

    return all_results, base_value


def _persist_shap_values(
    db: Session,
    scored_ids: list[int],
    shap_results: list[list[dict[str, object]]],
    base_value: float | None,
    model_version: str,
) -> int:
    """Upsert precomputed SHAP values into the property_shap_values table.

    Returns the number of rows upserted.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    now = datetime.now(tz=UTC)
    rows = [
        {
            "property_id": int(prop_id),
            "model_version": model_version,
            "shap_values": shap_list,
            "base_value": base_value,
            "computed_at": now,
        }
        for prop_id, shap_list in zip(scored_ids, shap_results, strict=True)
    ]

    if not rows:
        return 0

    stmt = pg_insert(PropertyShapValue).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_property_shap_prop_version",
        set_={
            "shap_values": stmt.excluded.shap_values,
            "base_value": stmt.excluded.base_value,
            "computed_at": stmt.excluded.computed_at,
        },
    )
    db.execute(stmt)
    return len(rows)


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

    logger.info("Loading features for %d properties", len(property_ids))
    features = load_feature_matrix(db, property_ids=property_ids)
    if features.empty:
        logger.info("No stored features; falling back to assembly")
        features = assemble_features(db, property_ids=property_ids)

    if features.empty:
        logger.warning("Feature matrix is empty; skipping batch scoring")
        return 0

    # Drop target column if present
    if "sold_price" in features.columns:
        features = features.drop(columns=["sold_price"])

    predictions = predict_batch(model, features)

    # Retrieve calibration residuals for conformal prediction intervals
    cal_residuals = getattr(model, "calibration_residuals_", None)

    # Batch SHAP computation (best-effort, non-blocking)
    try:
        shap_results, base_value = compute_shap_values_batch(model, features)
    except Exception:
        logger.error("Batch SHAP computation failed; skipping SHAP persistence", exc_info=True)
        shap_results = None
        base_value = None

    # Upsert predictions into property_valuations
    now = datetime.now(tz=UTC)
    scored_ids = features.index.tolist()

    for prop_id, pred_value in zip(scored_ids, predictions, strict=True):
        pred_float = float(pred_value)
        ci_low, ci_high = compute_confidence_interval(
            pred_float, metrics, calibration_residuals=cal_residuals
        )

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

    # Persist SHAP values after valuations are safely committed
    if shap_results is not None:
        try:
            shap_count = _persist_shap_values(
                db, scored_ids, shap_results, base_value, model_version
            )
            db.commit()
            logger.info("Persisted SHAP values for %d properties", shap_count)
        except Exception:
            logger.error("Failed to persist SHAP values; rolling back", exc_info=True)
            db.rollback()

    logger.info("Scored %d properties", len(scored_ids))
    return len(scored_ids)
