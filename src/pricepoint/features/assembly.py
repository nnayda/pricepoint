"""Feature assembly — combine all feature sets into a single training matrix."""

from __future__ import annotations

import logging
import time

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pricepoint.db.models import RedfinListing
from pricepoint.features.comparables import (
    build_comparable_features,
    build_training_comparable_features,
)
from pricepoint.features.economic import (
    build_economic_features,
    build_training_economic_features,
)
from pricepoint.features.geospatial import build_geospatial_features
from pricepoint.features.housing import build_housing_features, build_training_sale_events

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

    logger.info("[1/4] Building geospatial features...")
    t0 = time.monotonic()
    geo = build_geospatial_features(db, property_ids=property_ids)
    logger.info(
        "[1/4] Geospatial features complete: %s rows × %s cols in %.1fs",
        geo.shape[0],
        geo.shape[1],
        time.monotonic() - t0,
    )

    logger.info("[2/4] Building housing features...")
    t0 = time.monotonic()
    housing = build_housing_features(db, property_ids=property_ids)
    logger.info(
        "[2/4] Housing features complete: %s rows × %s cols in %.1fs",
        housing.shape[0],
        housing.shape[1],
        time.monotonic() - t0,
    )

    logger.info("[3/4] Building economic features...")
    t0 = time.monotonic()
    econ = build_economic_features(db, property_ids=property_ids)
    logger.info(
        "[3/4] Economic features complete: %s rows × %s cols in %.1fs",
        econ.shape[0],
        econ.shape[1],
        time.monotonic() - t0,
    )

    logger.info("[4/4] Building comparable sales features...")
    t0 = time.monotonic()
    comp = build_comparable_features(db, property_ids=property_ids)
    logger.info(
        "[4/4] Comparable features complete: %s rows × %s cols in %.1fs",
        comp.shape[0],
        comp.shape[1],
        time.monotonic() - t0,
    )

    logger.info(
        "Feature shapes — geo: %s, housing: %s, econ: %s, comp: %s",
        geo.shape,
        housing.shape,
        econ.shape,
        comp.shape,
    )

    t0 = time.monotonic()
    combined = pd.concat([geo, housing, econ, comp], axis=1)

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


def assemble_training_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
    min_sale_price: float = 10_000,
) -> pd.DataFrame:
    """Build an expanded training matrix with multiple rows per property.

    Creates one row per historical SOLD event, recalculating time-sensitive
    and economic features as-of each sale date.  Geospatial features are
    joined by ``property_id`` (same value for all events of a property).

    The result is used **only for model training** — the per-property
    feature store (used by inference) is not modified.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    property_ids:
        Limit to these property IDs.  ``None`` means all.
    min_sale_price:
        Minimum sale price to include (filters out nominal transfers).

    Returns
    -------
    pd.DataFrame
        Indexed by ``sale_event_id`` with ``property_id`` as a column.
    """
    id_desc = f"{len(property_ids)} properties" if property_ids else "all properties"
    logger.info("Starting training feature assembly for %s", id_desc)
    overall_start = time.monotonic()

    # 1. Housing features — multi-row, one per SOLD event
    logger.info("[1/4] Building training sale events (housing features)...")
    t0 = time.monotonic()
    housing = build_training_sale_events(
        db, property_ids=property_ids, min_sale_price=min_sale_price
    )
    logger.info(
        "[1/4] Training sale events: %s rows × %s cols in %.1fs",
        housing.shape[0],
        housing.shape[1],
        time.monotonic() - t0,
    )

    if housing.empty:
        logger.warning("No training sale events found")
        return pd.DataFrame()

    # Extract unique property IDs for geospatial lookup
    unique_property_ids = housing["property_id"].unique().tolist()

    # 2. Geospatial features — indexed by property_id, join via housing's property_id col
    logger.info("[2/4] Building geospatial features for %d properties...", len(unique_property_ids))
    t0 = time.monotonic()
    geo = build_geospatial_features(db, property_ids=unique_property_ids)
    logger.info(
        "[2/4] Geospatial features: %s rows × %s cols in %.1fs",
        geo.shape[0],
        geo.shape[1],
        time.monotonic() - t0,
    )

    # 3. Economic features — per sale event, using each event's sale_date
    logger.info("[3/4] Building training economic features...")
    t0 = time.monotonic()
    # Prepare the lookup DataFrame from housing (needs sale_event_id, property_id, sale_date)
    econ_input = housing[["property_id", "sale_date"]].copy()
    econ_input = econ_input.reset_index()  # sale_event_id becomes a column
    econ = build_training_economic_features(db, econ_input)
    logger.info(
        "[3/4] Training economic features: %s rows × %s cols in %.1fs",
        econ.shape[0],
        econ.shape[1],
        time.monotonic() - t0,
    )

    # 4. Comparable features — per sale event, using each event's sale_date
    logger.info("[4/4] Building training comparable features...")
    t0 = time.monotonic()
    # Need sale_event_id, property_id, sale_date, sqft, num_beds, num_baths, sold_price
    comp_cols = ["property_id", "sale_date", "sold_price"]
    # sqft and num_beds/baths may or may not be in the housing DataFrame (they're from listing)
    # We need to read them from the listings directly
    from pricepoint.db.models import RedfinListing as RL

    listing_query = db.query(RL.id, RL.sqft, RL.num_beds, RL.num_baths).filter(
        RL.id.in_(unique_property_ids)
    )
    listing_attrs = {
        r[0]: {"sqft": r[1], "num_beds": r[2], "num_baths": r[3]} for r in listing_query
    }

    comp_input = housing[comp_cols].copy().reset_index()
    comp_input["sqft"] = comp_input["property_id"].map(
        lambda pid: listing_attrs.get(pid, {}).get("sqft")
    )
    comp_input["num_beds"] = comp_input["property_id"].map(
        lambda pid: listing_attrs.get(pid, {}).get("num_beds")
    )
    comp_input["num_baths"] = comp_input["property_id"].map(
        lambda pid: listing_attrs.get(pid, {}).get("num_baths")
    )
    comp = build_training_comparable_features(db, comp_input)
    logger.info(
        "[4/4] Training comparable features: %s rows × %s cols in %.1fs",
        comp.shape[0],
        comp.shape[1],
        time.monotonic() - t0,
    )

    # Merge: housing + geo (via property_id) + econ (via sale_event_id) + comp (via sale_event_id)
    logger.info(
        "Merging feature sets — housing: %s, geo: %s, econ: %s, comp: %s",
        housing.shape,
        geo.shape,
        econ.shape,
        comp.shape,
    )

    # Join geo features onto housing via property_id
    combined = housing.join(geo, on="property_id", rsuffix="_geo")

    # Join econ and comp features via sale_event_id index
    combined = combined.join(econ, rsuffix="_econ")
    combined = combined.join(comp, rsuffix="_comp")

    # Drop rows where every feature column is NaN
    before_drop = len(combined)
    feature_cols = [
        c
        for c in combined.columns
        if c
        not in (
            "property_id",
            "sale_date",
            "sale_event_id",
            "is_historical",
            "record_age_years",
        )
    ]
    combined = combined.dropna(subset=feature_cols, how="all")
    dropped = before_drop - len(combined)
    if dropped:
        logger.info("Dropped %d all-NaN rows", dropped)

    elapsed = time.monotonic() - overall_start
    n_properties = combined["property_id"].nunique() if not combined.empty else 0
    expansion = len(combined) / n_properties if n_properties > 0 else 0
    logger.info(
        "Assembled training matrix: %s rows × %s cols for %d properties "
        "(%.1fx expansion, total time: %.1fs)",
        combined.shape[0],
        combined.shape[1],
        n_properties,
        expansion,
        elapsed,
    )
    return combined
