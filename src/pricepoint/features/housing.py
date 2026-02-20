"""Housing feature engineering.

Transforms raw housing data into model-ready features:
price per sqft, days on market, listing premium over assessment, etc.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy.orm import Session

from pricepoint.db.models import (
    PropertyValuation,
    RedfinListing,
    SaleHistoryRecord,
    TaxHistoryRecord,
)

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

    # days_on_market
    if listing.contract_date is not None:
        ref_date = listing.sold_date if listing.sold_date is not None else now
        contract = listing.contract_date
        # Normalize timezone awareness for subtraction
        if contract.tzinfo is None and ref_date.tzinfo is not None:
            contract = contract.replace(tzinfo=ref_date.tzinfo)
        elif contract.tzinfo is not None and ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=contract.tzinfo)
        delta = ref_date - contract
        result["days_on_market"] = delta.days
    else:
        result["days_on_market"] = None

    # bed_bath_ratio
    beds = listing.num_beds
    baths = listing.num_baths
    if beds is not None and baths is not None and baths != 0:
        result["bed_bath_ratio"] = beds / baths
    else:
        result["bed_bath_ratio"] = 0.0

    # sqft_per_bedroom
    sqft = listing.sqft
    if sqft is not None and beds is not None and beds != 0:
        result["sqft_per_bedroom"] = sqft / beds
    else:
        result["sqft_per_bedroom"] = 0.0

    # lot_to_building_ratio
    lot_sqft = listing.lot_size
    building_sqft = listing.building_area
    if lot_sqft is not None and building_sqft is not None and building_sqft != 0:
        result["lot_to_building_ratio"] = lot_sqft / building_sqft
    else:
        result["lot_to_building_ratio"] = 0.0

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

    return result


def _compute_price_features(
    listing: RedfinListing,
    latest_assessment: float | None,
) -> dict:
    """Compute price-derived features."""
    result: dict = {}

    # listing_premium_pct
    if (
        listing.listing_price is not None
        and latest_assessment is not None
        and latest_assessment != 0
    ):
        result["listing_premium_pct"] = (
            (listing.listing_price - latest_assessment) / latest_assessment * 100
        )
    else:
        result["listing_premium_pct"] = None

    # sale_premium_pct
    if (
        listing.sold_price is not None
        and listing.listing_price is not None
        and listing.listing_price != 0
    ):
        result["sale_premium_pct"] = (
            (listing.sold_price - listing.listing_price) / listing.listing_price * 100
        )
    else:
        result["sale_premium_pct"] = None

    # redfin_estimate_diff_pct - redfin_estimate is stored on PropertyValuation
    # We handle this in the main function using the valuation data
    return result


def _compute_tax_features(tax_records: list[TaxHistoryRecord]) -> dict:
    """Compute features from tax history records."""
    result: dict = {}

    if not tax_records:
        result["tax_assessed_value"] = None
        result["land_to_improvements_ratio"] = None
        result["effective_tax_rate"] = None
        return result

    # Sort by date descending to get latest
    sorted_records = sorted(tax_records, key=lambda r: r.date or datetime.min, reverse=True)
    latest = sorted_records[0]

    result["tax_assessed_value"] = latest.assessment_value

    # land_to_improvements_ratio
    land = latest.assessment_value_land
    improvements = latest.assessment_value_additions
    if land is not None and improvements is not None and improvements != 0:
        result["land_to_improvements_ratio"] = land / improvements
    else:
        result["land_to_improvements_ratio"] = None

    # effective_tax_rate
    tax = latest.property_tax
    assessed = latest.assessment_value
    if tax is not None and assessed is not None and assessed != 0:
        result["effective_tax_rate"] = tax / assessed
    else:
        result["effective_tax_rate"] = None

    return result


def _compute_sale_features(sale_records: list[SaleHistoryRecord], now: datetime) -> dict:
    """Compute features from sale history records."""
    result: dict = {}

    sold_events = [
        r for r in sale_records if r.event and r.event.upper() == "SOLD" and r.price is not None
    ]

    result["num_prior_sales"] = len(sold_events)

    # Sort sold events by date descending
    sold_dated = [s for s in sold_events if s.date is not None]
    sold_dated.sort(key=lambda r: r.date, reverse=True)  # type: ignore[arg-type]

    # years_since_last_sale
    if sold_dated:
        last_date = sold_dated[0].date  # type: ignore[union-attr]
        if last_date.tzinfo is None and now.tzinfo is not None:
            last_date = last_date.replace(tzinfo=now.tzinfo)
        delta = now - last_date  # type: ignore[operator]
        result["years_since_last_sale"] = delta.days / 365.25
    else:
        result["years_since_last_sale"] = None

    # price_yoy_change_pct - YoY change from last two SOLD events
    if len(sold_dated) >= 2:
        latest_price = sold_dated[0].price
        prev_price = sold_dated[1].price
        if prev_price and prev_price != 0:
            result["price_yoy_change_pct"] = (
                (latest_price - prev_price) / prev_price * 100  # type: ignore[operator]
            )
        else:
            result["price_yoy_change_pct"] = None
    else:
        result["price_yoy_change_pct"] = None

    return result


def _compute_zip_and_city_aggregates(db: Session, property_ids: list[int] | None) -> pd.DataFrame:
    """Compute location-based aggregate features using window functions.

    Returns DataFrame indexed by listing id with columns:
    zip_median_price, zip_median_price_per_sqft, zip_price_rank_pct, city_median_price
    """
    # Base query: recent sold listings
    base = db.query(
        RedfinListing.id.label("property_id"),
        RedfinListing.zip_code,
        RedfinListing.city,
        RedfinListing.sold_price,
        RedfinListing.price_per_sqft,
    ).filter(
        RedfinListing.sold_price.isnot(None),
    )

    if property_ids is not None:
        base = base.filter(RedfinListing.id.in_(property_ids))

    rows = base.all()

    if not rows:
        return pd.DataFrame(
            columns=[
                "property_id",
                "zip_median_price",
                "zip_median_price_per_sqft",
                "zip_price_rank_pct",
                "city_median_price",
            ]
        ).set_index("property_id")

    cols = ["property_id", "zip_code", "city", "sold_price", "price_per_sqft"]
    df = pd.DataFrame(rows, columns=cols)

    # zip_median_price
    zip_medians = df.groupby("zip_code")["sold_price"].transform("median")
    df["zip_median_price"] = zip_medians

    # zip_median_price_per_sqft
    df["zip_median_price_per_sqft"] = df.groupby("zip_code")["price_per_sqft"].transform("median")

    # zip_price_rank_pct
    df["zip_price_rank_pct"] = df.groupby("zip_code")["sold_price"].rank(pct=True, method="average")

    # city_median_price
    df["city_median_price"] = df.groupby("city")["sold_price"].transform("median")

    result = df[
        [
            "property_id",
            "zip_median_price",
            "zip_median_price_per_sqft",
            "zip_price_rank_pct",
            "city_median_price",
        ]
    ].set_index("property_id")

    return result


def build_housing_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Compute housing features for the given properties.

    Returns a DataFrame indexed by property ID with 22 feature columns.
    """
    now = datetime.now(tz=UTC)

    # Load listings
    query = db.query(RedfinListing)
    if property_ids is not None:
        query = query.filter(RedfinListing.id.in_(property_ids))
    listings: list[RedfinListing] = query.all()

    if not listings:
        return pd.DataFrame()

    listing_ids = [listing.id for listing in listings]

    # Bulk load related records
    tax_records = (
        db.query(TaxHistoryRecord).filter(TaxHistoryRecord.property_id.in_(listing_ids)).all()
    )
    sale_records = (
        db.query(SaleHistoryRecord).filter(SaleHistoryRecord.property_id.in_(listing_ids)).all()
    )

    # Load redfin estimate valuations
    redfin_valuations = (
        db.query(PropertyValuation)
        .filter(
            PropertyValuation.property_id.in_(listing_ids),
            PropertyValuation.source == "redfin",
        )
        .all()
    )

    # Group by property_id
    tax_by_prop: dict[int, list[TaxHistoryRecord]] = {}
    for t in tax_records:
        tax_by_prop.setdefault(t.property_id, []).append(t)

    sale_by_prop: dict[int, list[SaleHistoryRecord]] = {}
    for s in sale_records:
        sale_by_prop.setdefault(s.property_id, []).append(s)

    redfin_est_by_prop: dict[int, float] = {}
    for v in redfin_valuations:
        redfin_est_by_prop[v.property_id] = v.value

    # Build per-property features
    all_rows: list[dict] = []
    for listing in listings:
        pid = listing.id

        # Property-level features
        row = _compute_property_features(listing, now)

        # Tax features
        tax_feats = _compute_tax_features(tax_by_prop.get(pid, []))
        row.update(tax_feats)

        # Sale features
        sale_feats = _compute_sale_features(sale_by_prop.get(pid, []), now)
        row.update(sale_feats)

        # Price-derived features
        latest_assessment = tax_feats.get("tax_assessed_value")
        price_feats = _compute_price_features(listing, latest_assessment)
        row.update(price_feats)

        # redfin_estimate_diff_pct
        redfin_est = redfin_est_by_prop.get(pid)
        if listing.listing_price is not None and redfin_est is not None and redfin_est != 0:
            row["redfin_estimate_diff_pct"] = (
                (listing.listing_price - redfin_est) / redfin_est * 100
            )
        else:
            row["redfin_estimate_diff_pct"] = None

        all_rows.append(row)

    df = pd.DataFrame(all_rows).set_index("property_id")

    # Compute location aggregates and merge
    agg_df = _compute_zip_and_city_aggregates(db, property_ids)
    if not agg_df.empty:
        df = df.join(agg_df, how="left")
    else:
        df["zip_median_price"] = None
        df["zip_median_price_per_sqft"] = None
        df["zip_price_rank_pct"] = None
        df["city_median_price"] = None

    return df
