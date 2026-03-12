"""Feature assembly — combine all feature sets into a single training matrix."""

from __future__ import annotations

import logging
import time

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pricepoint.db.models import RedfinListing
from pricepoint.features.economic import build_economic_features
from pricepoint.features.geospatial import build_geospatial_features
from pricepoint.features.housing import build_housing_features

logger = logging.getLogger(__name__)


def get_stale_property_ids(db: Session) -> list[int]:
    """Find properties needing feature recomputation (NULL features_built_at)."""
    return list(
        db.execute(
            select(RedfinListing.id).where(
                RedfinListing.location.isnot(None),
                RedfinListing.features_built_at.is_(None),
            )
        )
        .scalars()
        .all()
    )


def reset_features_built_at(db: Session) -> int:
    """Mark all properties as needing feature recomputation.

    Sets ``features_built_at`` to NULL so that the next feature assembly
    run will reprocess them.  Called at the start of a DAG-triggered run
    (since the trigger means upstream data changed).
    """
    result = db.execute(
        update(RedfinListing)
        .where(RedfinListing.features_built_at.isnot(None))
        .values(features_built_at=None)
    )
    db.commit()
    count = result.rowcount or 0  # type: ignore[attr-defined]
    if count:
        logger.info("Reset features_built_at for %d properties", count)
    return count


def assemble_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Join geospatial, housing, and economic features into a unified feature matrix.

    Calls all three feature builder functions, merges the resulting DataFrames
    on the ``property_id`` index (column-wise), drops rows that are entirely
    NaN, and returns the combined DataFrame ready for model training.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    property_ids:
        Limit to these property IDs.  ``None`` means all.

    Returns
    -------
    pd.DataFrame
        Indexed by ``property_id`` with all feature columns.
    """
    id_desc = f"{len(property_ids)} properties" if property_ids else "all properties"
    logger.info("Starting feature assembly for %s", id_desc)
    overall_start = time.monotonic()

    logger.info("[1/3] Building geospatial features...")
    t0 = time.monotonic()
    geo = build_geospatial_features(db, property_ids=property_ids)
    logger.info(
        "[1/3] Geospatial features complete: %s rows × %s cols in %.1fs",
        geo.shape[0],
        geo.shape[1],
        time.monotonic() - t0,
    )

    logger.info("[2/3] Building housing features...")
    t0 = time.monotonic()
    housing = build_housing_features(db, property_ids=property_ids)
    logger.info(
        "[2/3] Housing features complete: %s rows × %s cols in %.1fs",
        housing.shape[0],
        housing.shape[1],
        time.monotonic() - t0,
    )

    logger.info("[3/3] Building economic features...")
    t0 = time.monotonic()
    econ = build_economic_features(db, property_ids=property_ids)
    logger.info(
        "[3/3] Economic features complete: %s rows × %s cols in %.1fs",
        econ.shape[0],
        econ.shape[1],
        time.monotonic() - t0,
    )

    logger.info(
        "Feature shapes — geo: %s, housing: %s, econ: %s",
        geo.shape,
        housing.shape,
        econ.shape,
    )

    t0 = time.monotonic()
    combined = pd.concat([geo, housing, econ], axis=1)

    # Drop rows where every column is NaN
    before_drop = len(combined)
    combined = combined.dropna(how="all")
    dropped = before_drop - len(combined)
    if dropped:
        logger.info("Dropped %d all-NaN rows", dropped)

    elapsed = time.monotonic() - overall_start
    logger.info(
        "Assembled feature matrix: %s rows × %s cols (total time: %.1fs)",
        combined.shape[0],
        combined.shape[1],
        elapsed,
    )
    return combined
