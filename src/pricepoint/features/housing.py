"""Housing feature engineering.

Transforms raw housing data into model-ready features:
price per sqft, bed/bath ratios, amenity scores, boolean/categorical features, etc.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from math import exp

import pandas as pd
from sqlalchemy.orm import Session

from pricepoint.db.models import (
    RedfinListing,
    SaleHistoryRecord,
)

logger = logging.getLogger(__name__)

# Boolean columns on RedfinListing considered "luxury" features
LUXURY_COLUMNS: list[str] = [
    "has_private_pool",
    "has_outdoor_kitchen",
    "has_sport_court",
    "has_sauna",
    "has_outdoor_fireplace",
    "has_ev_charging",
    "is_waterfront",
    "has_clubhouse",
]

# All boolean amenity columns on RedfinListing
AMENITY_COLUMNS: list[str] = [
    "has_garage",
    "has_workshop",
    "has_circular_driveway",
    "has_ev_charging",
    "has_fireplace",
    "has_outdoor_fireplace",
    "has_primary_fireplace",
    "has_architectural_fireplace",
    "has_drink_fridge",
    "has_stainless_appliances",
    "has_efficient_windows",
    "has_skylights",
    "has_bay_window",
    "has_laundry_room",
    "has_utility_sink",
    "is_primary_downstairs",
    "has_guest_suite",
    "has_butler_pantry",
    "has_walkin_closets",
    "has_tall_ceilings",
    "has_luxury_ceilings",
    "has_sauna",
    "has_bar",
    "has_second_primary",
    "has_room_over_garage",
    "has_open_floorplan",
    "is_carpet_free",
    "has_premium_stone",
    "has_hardwood",
    "has_enclosed_porch",
    "has_front_porch",
    "has_fenced_yard",
    "has_outdoor_kitchen",
    "has_sport_court",
    "has_private_pool",
    "has_community_pool",
    "has_clubhouse",
    "has_exterior_storage",
    "has_garden",
    "is_waterfront",
]

CATEGORICAL_COLUMNS: list[str] = [
    "parking_type",
    "garage_entry",
    "driveway_surface",
    "laundry_location",
    "countertop_material",
    "facade_type",
]

BOOLEAN_FEATURE_COLUMNS: list[str] = [
    "has_garage",
    "has_workshop",
    "has_circular_driveway",
    "has_ev_charging",
    "has_fireplace",
    "has_outdoor_fireplace",
    "has_efficient_windows",
    "has_skylights",
    "has_bay_window",
    "has_laundry_room",
    "has_utility_sink",
    "is_primary_downstairs",
    "has_guest_suite",
    "has_butler_pantry",
    "has_walkin_closets",
    "has_tall_ceilings",
    "has_luxury_ceilings",
    "has_sauna",
    "has_bar",
    "has_second_primary",
    "has_room_over_garage",
    "has_open_floorplan",
    "is_carpet_free",
    "has_premium_stone",
    "has_hardwood",
    "has_crawl_space",
    "is_waterfront",
    "is_septic",
    "is_well_water",
    "no_heating",
    "no_cooling",
    "has_hoa",
    "has_enclosed_porch",
    "has_front_porch",
    "has_fenced_yard",
    "has_outdoor_kitchen",
    "has_sport_court",
    "has_private_pool",
    "has_community_pool",
    "has_clubhouse",
    "has_exterior_storage",
    "has_garden",
]

NUMERIC_LISTING_COLUMNS: list[str] = [
    "flood_score",
    "fire_score",
    "num_garage_spaces",
    "num_parking_spaces",
    "appliances_included_count",
    "association_fee",
]

DECAY_LAMBDA = 0.15


def _current_year() -> int:
    """Return the current year (UTC)."""
    return datetime.now(tz=UTC).year


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Divide numerator by denominator, returning None on zero/None denominator."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _compute_property_features(listing: RedfinListing, now: datetime) -> dict:
    """Compute property-level features from a single RedfinListing row."""
    current_year = now.year
    result: dict = {"property_id": listing.id}

    # Target column — needed by the training pipeline
    result["sold_price"] = listing.sold_price

    # property_age
    result["property_age"] = (
        (current_year - listing.year_built) if listing.year_built is not None else None
    )

    # is_renovated
    result["is_renovated"] = listing.year_renovated is not None

    # years_since_renovation
    result["years_since_renovation"] = (
        (current_year - listing.year_renovated) if listing.year_renovated is not None else None
    )

    # bed_bath_ratio
    beds = listing.num_beds
    baths = listing.num_baths
    if beds is not None and baths is not None and baths != 0:
        result["bed_bath_ratio"] = beds / baths
    else:
        result["bed_bath_ratio"] = None

    # sqft_per_bedroom
    sqft = listing.sqft
    if sqft is not None and beds is not None and beds != 0:
        result["sqft_per_bedroom"] = sqft / beds
    else:
        result["sqft_per_bedroom"] = None

    # lot_to_building_ratio
    lot_sqft = listing.lot_size
    building_sqft = listing.building_area
    if lot_sqft is not None and building_sqft is not None and building_sqft != 0:
        result["lot_to_building_ratio"] = lot_sqft / building_sqft
    else:
        result["lot_to_building_ratio"] = None

    # luxury_feature_count
    luxury_count = 0
    for col in LUXURY_COLUMNS:
        if getattr(listing, col, False):
            luxury_count += 1
    result["luxury_feature_count"] = luxury_count

    # amenity_score
    amenity_count = 0
    for col in AMENITY_COLUMNS:
        if getattr(listing, col, False):
            amenity_count += 1
    result["amenity_score"] = amenity_count

    # Boolean feature columns
    for col in BOOLEAN_FEATURE_COLUMNS:
        result[col] = bool(getattr(listing, col, False))

    # Numeric listing columns
    for col in NUMERIC_LISTING_COLUMNS:
        result[col] = getattr(listing, col, None)

    # Categorical columns
    for col in CATEGORICAL_COLUMNS:
        result[col] = getattr(listing, col, None)

    return result


def _compute_sale_features(sale_records: list[SaleHistoryRecord], now: datetime) -> dict:
    """Compute features from sale history records."""
    result: dict = {}

    sold_events = [
        r for r in sale_records if r.event and r.event.upper() == "SOLD" and r.price is not None
    ]

    # Sort sold events by date descending
    sold_dated = [s for s in sold_events if s.date is not None]
    sold_dated.sort(key=lambda r: r.date or datetime.min, reverse=True)

    # years_since_last_sale
    if sold_dated:
        last_date = sold_dated[0].date
        if last_date is not None and last_date.tzinfo is None and now.tzinfo is not None:
            last_date = last_date.replace(tzinfo=now.tzinfo)
        delta = now - last_date  # type: ignore[operator]
        result["years_since_last_sale"] = delta.days / 365.25

        # decayed_sale_signal
        last_sold_price = sold_dated[0].price
        if last_sold_price is not None:
            result["decayed_sale_signal"] = last_sold_price * exp(
                -DECAY_LAMBDA * result["years_since_last_sale"]
            )
        else:
            result["decayed_sale_signal"] = None
    else:
        result["years_since_last_sale"] = None
        result["decayed_sale_signal"] = None

    return result


def build_housing_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute housing features for the given properties.

    Returns a DataFrame indexed by property ID with feature columns.
    """
    now = datetime.now(tz=UTC)

    # Load listings
    logger.info("Loading listings from database...")
    t0 = time.monotonic()
    query = db.query(RedfinListing)
    if property_ids is not None:
        query = query.filter(RedfinListing.id.in_(property_ids))
    listings: list[RedfinListing] = query.all()
    logger.info("Loaded %d listings in %.1fs", len(listings), time.monotonic() - t0)

    if not listings:
        return pd.DataFrame()

    listing_ids = [listing.id for listing in listings]

    # Bulk load sale records
    logger.info("Bulk-loading sale records...")
    t0 = time.monotonic()
    sale_records = (
        db.query(SaleHistoryRecord).filter(SaleHistoryRecord.property_id.in_(listing_ids)).all()
    )
    logger.info(
        "Loaded %d sale records in %.1fs",
        len(sale_records),
        time.monotonic() - t0,
    )

    # Group by property_id
    sale_by_prop: dict[int, list[SaleHistoryRecord]] = {}
    for s in sale_records:
        sale_by_prop.setdefault(s.property_id, []).append(s)

    # Build per-property features
    logger.info("Computing per-property features for %d listings...", len(listings))
    t0 = time.monotonic()
    all_rows: list[dict] = []
    for listing in listings:
        pid = listing.id

        # Property-level features
        row = _compute_property_features(listing, now)

        # Sale features
        sale_feats = _compute_sale_features(sale_by_prop.get(pid, []), now)
        row.update(sale_feats)

        all_rows.append(row)

    df = pd.DataFrame(all_rows).set_index("property_id")
    logger.info("Per-property features computed in %.1fs", time.monotonic() - t0)

    # Cast categorical columns
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df
