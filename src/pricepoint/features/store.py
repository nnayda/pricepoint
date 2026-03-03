"""Feature store — persist and retrieve assembled feature matrices.

Provides helpers to save the output of ``assemble_features()`` into the
``property_features`` table and load it back as a DataFrame, so that
downstream consumers (model training, SHAP API, batch scoring) don't
have to re-run the full feature engineering pipeline.
"""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pricepoint.db.models import PropertyFeature

logger = logging.getLogger(__name__)


def _feature_hash(feature_names: list[str]) -> str:
    """Return a SHA-256 hex digest of the sorted feature column names.

    Used for drift detection — when the hash changes, the feature schema
    has been modified.
    """
    joined = ",".join(sorted(feature_names))
    return hashlib.sha256(joined.encode()).hexdigest()


def _sanitize_value(v: object) -> object:
    """Convert NaN/inf floats to None for JSON storage."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def save_feature_matrix(db: Session, df: pd.DataFrame) -> int:
    """Upsert a feature DataFrame into the ``property_features`` table.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    df:
        Feature matrix indexed by ``property_id``.

    Returns
    -------
    int
        Number of rows upserted.
    """
    if df.empty:
        logger.warning("Empty feature matrix — nothing to save")
        return 0

    feature_cols = [c for c in df.columns if c != "sold_price"]
    fhash = _feature_hash(feature_cols)
    now = datetime.now(tz=UTC)

    rows: list[dict] = []
    for property_id, row in df.iterrows():
        features_dict = {col: _sanitize_value(row[col]) for col in feature_cols}
        rows.append(
            {
                "property_id": int(property_id),
                "features": features_dict,
                "feature_hash": fhash,
                "computed_at": now,
                "updated_at": now,
            }
        )

    stmt = pg_insert(PropertyFeature).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["property_id"],
        set_={
            "features": stmt.excluded.features,
            "feature_hash": stmt.excluded.feature_hash,
            "computed_at": stmt.excluded.computed_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    db.commit()

    logger.info("Saved %d feature rows (hash=%s…)", len(rows), fhash[:12])
    return len(rows)


def load_feature_matrix(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Load persisted features as a DataFrame.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    property_ids:
        Limit to these property IDs.  ``None`` means all.

    Returns
    -------
    pd.DataFrame
        Indexed by ``property_id`` with feature columns.  Empty DataFrame
        if no rows match.
    """
    query = db.query(PropertyFeature)
    if property_ids is not None:
        query = query.filter(PropertyFeature.property_id.in_(property_ids))

    records = query.all()
    if not records:
        return pd.DataFrame()

    data: list[dict] = []
    for rec in records:
        row = dict(rec.features)
        row["property_id"] = rec.property_id
        data.append(row)

    df = pd.DataFrame(data).set_index("property_id")
    logger.info("Loaded %d feature rows (%d columns)", len(df), len(df.columns))
    return df


def load_single_property_features(
    db: Session,
    property_id: int,
) -> pd.DataFrame:
    """Load persisted features for a single property.

    Convenience wrapper around :func:`load_feature_matrix` for the
    common case of retrieving one row (e.g. SHAP API).

    Returns
    -------
    pd.DataFrame
        Single-row DataFrame indexed by ``property_id``, or empty.
    """
    return load_feature_matrix(db, property_ids=[property_id])


def delete_property_features(
    db: Session,
    property_ids: list[int],
) -> int:
    """Delete stored features for the given property IDs.

    Returns
    -------
    int
        Number of rows deleted.
    """
    if not property_ids:
        return 0
    result = db.execute(
        delete(PropertyFeature).where(PropertyFeature.property_id.in_(property_ids))
    )
    db.commit()
    return result.rowcount  # type: ignore[union-attr,return-value]
