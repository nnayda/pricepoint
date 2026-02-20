"""Feature assembly — combine all feature sets into a single training matrix."""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy.orm import Session

from pricepoint.features.economic import build_economic_features
from pricepoint.features.geospatial import build_geospatial_features
from pricepoint.features.housing import build_housing_features

logger = logging.getLogger(__name__)


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
    geo = build_geospatial_features(db, property_ids=property_ids)
    housing = build_housing_features(db, property_ids=property_ids)
    econ = build_economic_features(db, property_ids=property_ids)

    logger.info(
        "Feature shapes — geo: %s, housing: %s, econ: %s",
        geo.shape,
        housing.shape,
        econ.shape,
    )

    combined = pd.concat([geo, housing, econ], axis=1)

    # Drop rows where every column is NaN
    combined = combined.dropna(how="all")

    logger.info("Assembled feature matrix: %s", combined.shape)
    return combined
