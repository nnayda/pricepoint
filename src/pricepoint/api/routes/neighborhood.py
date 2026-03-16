"""Neighborhood valuation endpoints — aggregates home values within a census tract."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import (
    ST_X,
    ST_Y,
    ST_AsGeoJSON,
    ST_Contains,
    ST_DWithin,
    ST_MakePoint,
    ST_SetSRID,
    ST_Simplify,
)
from sqlalchemy import Date, Float, case, cast, func, literal_column, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.neighborhood import (
    NeighborhoodMedianPoint,
    NeighborhoodPropertiesResponse,
    NeighborhoodPropertyPoint,
    NeighborhoodValuationHistoryResponse,
    NeighborhoodValuationResponse,
)
from pricepoint.db.models import (
    PropertyGeoLookup,
    PropertyValuation,
    RedfinListing,
    SaleHistoryRecord,
    Tract,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["neighborhood"])

_ACTIVE_STATUSES = {"for sale", "contingent", "pending", "under contract"}
_MIN_SAMPLE_SIZE = 5


@router.get("/neighborhood/valuation", response_model=NeighborhoodValuationResponse)
async def get_neighborhood_valuation(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
) -> NeighborhoodValuationResponse:
    """Return median and max home values for the census tract containing the point."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # 1. Find census tract — try precomputed lookup first
    tract_geoid: str | None = None
    tract_geom = None

    lookup = db.execute(
        select(PropertyGeoLookup.census_tract_geoid)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if lookup:
        tract_geoid = lookup
        # Fetch tract geometry for listing containment query
        tract_geom_row = db.execute(
            select(Tract.geom).where(Tract.geoid == tract_geoid).limit(1)
        ).scalar_one_or_none()
        tract_geom = tract_geom_row
    else:
        # Fallback: spatial containment for unlisted addresses
        tract_row = db.execute(
            select(Tract.geoid, Tract.geom).where(ST_Contains(Tract.geom, point)).limit(1)
        ).first()
        if tract_row:
            tract_geoid = str(tract_row.geoid)
            tract_geom = tract_row.geom

    if not tract_geoid or tract_geom is None:
        return NeighborhoodValuationResponse(
            tract_geoid="unknown",
            median_value=None,
            max_value=None,
            sample_size=0,
        )

    # 2. Build effective price expression
    two_years_ago = datetime.now(tz=UTC) - timedelta(days=730)

    # ML model fallback via lateral subquery
    ml_value = (
        select(PropertyValuation.value)
        .where(
            PropertyValuation.property_id == RedfinListing.id,
            PropertyValuation.source == "ml_model",
        )
        .order_by(PropertyValuation.estimated_at.desc())
        .limit(1)
        .correlate(RedfinListing)
        .scalar_subquery()
    )

    effective_price = case(
        # Priority 1: active listing → listing_price
        (
            func.lower(RedfinListing.listing_status).in_(_ACTIVE_STATUSES),
            RedfinListing.listing_price,
        ),
        # Priority 2: sold within 2 years → sold_price
        (
            RedfinListing.sold_date >= two_years_ago,
            RedfinListing.sold_price,
        ),
        # Priority 3: ML model estimate
        else_=ml_value,
    )

    effective_price_cast = cast(effective_price, Float).label("effective_price")

    # 3. Query listings in tract with effective price
    base_q = (
        select(effective_price_cast)
        .join(PropertyGeoLookup, PropertyGeoLookup.property_id == RedfinListing.id)
        .where(
            PropertyGeoLookup.census_tract_geoid == tract_geoid,
            RedfinListing.location.isnot(None),
        )
    )

    # Sub-select only rows with non-null effective price
    priced = base_q.subquery()
    priced_col = priced.c.effective_price

    stats = db.execute(
        select(
            func.count(priced_col).label("cnt"),
            func.percentile_cont(0.5).within_group(priced_col).label("median"),
            func.max(priced_col).label("max_val"),
        ).where(priced_col.isnot(None))
    ).first()

    if not stats:
        return NeighborhoodValuationResponse(
            tract_geoid=tract_geoid,
            median_value=None,
            max_value=None,
            sample_size=0,
        )

    sample_size: int = stats.cnt
    if sample_size < _MIN_SAMPLE_SIZE:
        return NeighborhoodValuationResponse(
            tract_geoid=tract_geoid,
            median_value=None,
            max_value=None,
            sample_size=sample_size,
        )

    return NeighborhoodValuationResponse(
        tract_geoid=tract_geoid,
        median_value=round(float(stats.median), 2) if stats.median is not None else None,
        max_value=round(float(stats.max_val), 2) if stats.max_val is not None else None,
        sample_size=sample_size,
    )


# ---------------------------------------------------------------------------
# Neighborhood valuation history — monthly median time series
# ---------------------------------------------------------------------------

_HOLD_MONTHS = 12
_MIN_PROPERTIES_PER_MONTH = 3


def _month_key(d: date) -> str:
    """Return 'YYYY-MM' string for the first of the month."""
    return f"{d.year:04d}-{d.month:02d}"


def _add_months(d: date, months: int) -> date:
    """Shift a date by *months* calendar months (clamps day to month length)."""
    total = d.year * 12 + (d.month - 1) + months
    y, m = divmod(total, 12)
    m += 1
    # Clamp day
    import calendar

    max_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, max_day))


def _generate_month_keys(start: date, end: date) -> list[str]:
    """Return sorted 'YYYY-MM' keys from *start* to *end* inclusive (first-of-month)."""
    keys: list[str] = []
    cur = date(start.year, start.month, 1)
    end_first = date(end.year, end.month, 1)
    while cur <= end_first:
        keys.append(_month_key(cur))
        cur = _add_months(cur, 1)
    return keys


def _interpolate_property_sales(
    sales: list[tuple[date, float]],
) -> dict[str, float]:
    """Linearly interpolate monthly values from sale events.

    * Holds flat for 12 months before the first sale and after the last.
    * Single-sale properties produce a flat line ± 12 months.
    """
    if not sales:
        return {}

    sorted_sales = sorted(sales, key=lambda s: s[0])
    first_date, last_date = sorted_sales[0][0], sorted_sales[-1][0]
    range_start = _add_months(first_date, -_HOLD_MONTHS)
    range_end = _add_months(last_date, _HOLD_MONTHS)
    month_keys = _generate_month_keys(range_start, range_end)

    result: dict[str, float] = {}

    for mk in month_keys:
        y, m = int(mk[:4]), int(mk[5:7])
        cur = date(y, m, 15)  # mid-month representative

        if cur <= first_date:
            result[mk] = sorted_sales[0][1]
        elif cur >= last_date:
            result[mk] = sorted_sales[-1][1]
        else:
            # Find surrounding sale events
            for i in range(len(sorted_sales) - 1):
                d0, v0 = sorted_sales[i]
                d1, v1 = sorted_sales[i + 1]
                if d0 <= cur <= d1:
                    span = (d1 - d0).days
                    if span == 0:
                        result[mk] = v1
                    else:
                        frac = (cur - d0).days / span
                        result[mk] = v0 + frac * (v1 - v0)
                    break

    return result


@router.get(
    "/neighborhood/valuation/history",
    response_model=NeighborhoodValuationHistoryResponse,
)
async def get_neighborhood_valuation_history(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
) -> NeighborhoodValuationHistoryResponse:
    """Return monthly median home-value time series for the census tract."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # 1. Find census tract — try precomputed lookup first
    tract_geoid: str | None = None

    lookup = db.execute(
        select(PropertyGeoLookup.census_tract_geoid)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if lookup:
        tract_geoid = lookup
    else:
        # Fallback: spatial containment for unlisted addresses
        tract_row = db.execute(
            select(Tract.geoid, Tract.geom).where(ST_Contains(Tract.geom, point)).limit(1)
        ).first()
        if tract_row:
            tract_geoid = str(tract_row.geoid)

    if not tract_geoid:
        return NeighborhoodValuationHistoryResponse(
            tract_geoid="unknown", sample_size=0, monthly_medians=[]
        )

    # 2. Get property IDs within tract via lookup table
    prop_ids_q = (
        select(RedfinListing.id)
        .join(PropertyGeoLookup, PropertyGeoLookup.property_id == RedfinListing.id)
        .where(PropertyGeoLookup.census_tract_geoid == tract_geoid)
    )
    prop_id_rows = db.execute(prop_ids_q).all()
    prop_ids = [r[0] for r in prop_id_rows]

    if not prop_ids:
        return NeighborhoodValuationHistoryResponse(
            tract_geoid=tract_geoid, sample_size=0, monthly_medians=[]
        )

    # 3. Fetch sale history records (filter nulls)
    sale_rows = db.execute(
        select(
            SaleHistoryRecord.property_id,
            SaleHistoryRecord.date,
            SaleHistoryRecord.price,
        ).where(
            SaleHistoryRecord.property_id.in_(prop_ids),
            SaleHistoryRecord.date.isnot(None),
            SaleHistoryRecord.price.isnot(None),
            SaleHistoryRecord.price > 0,
        )
    ).all()

    if not sale_rows:
        return NeighborhoodValuationHistoryResponse(
            tract_geoid=tract_geoid, sample_size=0, monthly_medians=[]
        )

    # 4. Group by property and interpolate
    by_property: dict[int, list[tuple[date, float]]] = defaultdict(list)
    for row in sale_rows:
        sale_date = row.date
        if isinstance(sale_date, datetime):
            sale_date = sale_date.date()
        by_property[row.property_id].append((sale_date, float(row.price)))

    # Interpolate each property
    all_interp: list[dict[str, float]] = []
    for sales in by_property.values():
        interp = _interpolate_property_sales(sales)
        if interp:
            all_interp.append(interp)

    sample_size = len(all_interp)

    # 5. Compute monthly medians (require >= 3 properties per month)
    all_months: set[str] = set()
    for interp in all_interp:
        all_months.update(interp.keys())

    monthly_medians: list[NeighborhoodMedianPoint] = []
    for mk in sorted(all_months):
        values = [interp[mk] for interp in all_interp if mk in interp]
        if len(values) >= _MIN_PROPERTIES_PER_MONTH:
            monthly_medians.append(
                NeighborhoodMedianPoint(date=mk, median_value=round(median(values), 2))
            )

    return NeighborhoodValuationHistoryResponse(
        tract_geoid=tract_geoid,
        sample_size=sample_size,
        monthly_medians=monthly_medians,
    )


# ---------------------------------------------------------------------------
# Neighborhood valuation properties — individual property points
# ---------------------------------------------------------------------------


@router.get(
    "/neighborhood/valuation/properties",
    response_model=NeighborhoodPropertiesResponse,
)
async def get_neighborhood_valuation_properties(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
) -> NeighborhoodPropertiesResponse:
    """Return individual properties in the census tract with their effective prices."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # 1. Find census tract
    tract_geoid: str | None = None

    lookup = db.execute(
        select(PropertyGeoLookup.census_tract_geoid)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if lookup:
        tract_geoid = lookup
    else:
        tract_row = db.execute(
            select(Tract.geoid).where(ST_Contains(Tract.geom, point)).limit(1)
        ).scalar_one_or_none()
        if tract_row:
            tract_geoid = str(tract_row)

    if not tract_geoid:
        return NeighborhoodPropertiesResponse(tract_geoid="unknown", sample_size=0, properties=[])

    # 2. Fetch tract boundary as GeoJSON for the frontend map overlay
    tract_boundary: dict | None = None
    tract_geojson_row = db.execute(
        select(ST_AsGeoJSON(ST_Simplify(Tract.geom, 0.0001)).label("geojson"))
        .where(Tract.geoid == tract_geoid)
        .limit(1)
    ).scalar_one_or_none()
    if tract_geojson_row:
        tract_boundary = json.loads(tract_geojson_row)

    # 3. Build effective price expression (same logic as valuation endpoint)
    two_years_ago = datetime.now(tz=UTC) - timedelta(days=730)

    ml_value = (
        select(PropertyValuation.value)
        .where(
            PropertyValuation.property_id == RedfinListing.id,
            PropertyValuation.source == "ml_model",
        )
        .order_by(PropertyValuation.estimated_at.desc())
        .limit(1)
        .correlate(RedfinListing)
        .scalar_subquery()
    )

    effective_price = case(
        (
            func.lower(RedfinListing.listing_status).in_(_ACTIVE_STATUSES),
            RedfinListing.listing_price,
        ),
        (
            RedfinListing.sold_date >= two_years_ago,
            RedfinListing.sold_price,
        ),
        else_=ml_value,
    )

    listing_status_label = case(
        (
            func.lower(RedfinListing.listing_status).in_(_ACTIVE_STATUSES),
            func.initcap(RedfinListing.listing_status),
        ),
        (
            RedfinListing.sold_date >= two_years_ago,
            literal_column("'Sold'"),
        ),
        else_=literal_column("'Estimated'"),
    )

    # 4. Query individual listings in tract
    rows = db.execute(
        select(
            RedfinListing.street_address,
            ST_Y(RedfinListing.location).label("lat"),
            ST_X(RedfinListing.location).label("lon"),
            cast(effective_price, Float).label("effective_price"),
            listing_status_label.label("listing_status"),
            cast(RedfinListing.sold_date, Date).label("sold_date"),
        )
        .join(PropertyGeoLookup, PropertyGeoLookup.property_id == RedfinListing.id)
        .where(
            PropertyGeoLookup.census_tract_geoid == tract_geoid,
            RedfinListing.location.isnot(None),
        )
    ).all()

    properties = [
        NeighborhoodPropertyPoint(
            address=row.street_address or "Unknown",
            lat=float(row.lat),
            lon=float(row.lon),
            effective_price=round(float(row.effective_price), 2),
            listing_status=row.listing_status or "Unknown",
            sold_date=row.sold_date.isoformat() if row.sold_date else None,
        )
        for row in rows
        if row.effective_price is not None
    ]

    return NeighborhoodPropertiesResponse(
        tract_geoid=tract_geoid,
        sample_size=len(properties),
        properties=properties,
        tract_boundary=tract_boundary,
    )
