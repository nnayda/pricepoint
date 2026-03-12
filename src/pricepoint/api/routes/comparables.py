"""Comparables endpoint — finds and ranks similar sold properties."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from typing import cast as type_cast

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.comparables import (
    ComparablesResponse,
    CompProperty,
    FeatureGroup,
)
from pricepoint.api.services.comparables_nn import find_nearest_comparables
from pricepoint.api.services.feature_categories import group_features
from pricepoint.api.services.nuisance_risk_helpers import (
    query_nuisance_sources,
    query_risk_features,
)
from pricepoint.db.models import (
    LlmPhotoScore,
    LlmQualityScore,
    PropertyGeoLookup,
    RedfinListing,
)
from pricepoint.features.assembly import assemble_features

logger = logging.getLogger(__name__)

router = APIRouter(tags=["comparables"])

METERS_PER_MILE = 1609.344


def _months_ago(months: int) -> datetime:
    """Return a UTC datetime ``months`` months in the past."""
    now = datetime.now(tz=UTC)
    # Approximate: 30 days per month
    return now - timedelta(days=30 * months)


def _build_comp_property(
    prop: RedfinListing,
    db: Session,
    *,
    feature_row: dict | None = None,
    similarity_distance: float | None = None,
) -> CompProperty:
    """Build a CompProperty schema from a RedfinListing row."""
    # Extract lat/lon
    lat, lon = 0.0, 0.0
    if prop.location is not None:
        coords = db.execute(
            select(
                func.ST_Y(prop.location).label("lat"),
                func.ST_X(prop.location).label("lon"),
            )
        ).one()
        lat, lon = coords.lat, coords.lon

    # Photos
    photos: list[str] = []
    if prop.property_photos:
        photos = [f"/api/photos/{p}" for p in prop.property_photos[:10]]

    # LLM scores
    desc_score = db.execute(
        select(LlmQualityScore.quality_score)
        .where(LlmQualityScore.listing_id == prop.id)
        .order_by(LlmQualityScore.extracted_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    photo_score = db.execute(
        select(LlmPhotoScore.visual_quality_score)
        .where(LlmPhotoScore.listing_id == prop.id)
        .order_by(LlmPhotoScore.extracted_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    # Feature groups
    feature_groups: list[FeatureGroup] = []
    if feature_row:
        grouped = group_features(feature_row)
        for cat, feats in grouped.items():
            feature_groups.append(
                FeatureGroup(
                    category=cat,
                    features=type_cast(dict[str, "float | str | bool | None"], feats),
                )
            )

    # Nuisances & risks
    nuisances = query_nuisance_sources(db, lat, lon) if lat and lon else []
    risks = query_risk_features(db, lat, lon) if lat and lon else []

    return CompProperty(
        listing_id=prop.id,
        address=prop.street_address or "",
        city=prop.city or "",
        state=prop.state or "",
        zip_code=prop.zip_code or "",
        lat=lat,
        lon=lon,
        sold_price=prop.sold_price,
        sold_date=prop.sold_date.strftime("%Y-%m-%d") if prop.sold_date else None,
        listing_price=prop.listing_price,
        beds=prop.num_beds or 0,
        baths=prop.num_baths or 0.0,
        sqft=prop.sqft,
        lot_size=prop.lot_size,
        year_built=prop.year_built,
        garage_spaces=prop.num_garage_spaces or 0,
        price_per_sqft=prop.price_per_sqft,
        photos=photos,
        description_score=desc_score,
        photo_score=photo_score,
        feature_groups=feature_groups,
        nuisances=nuisances,
        risks=risks,
        similarity_distance=similarity_distance,
    )


@router.get("/comparables/search", response_model=ComparablesResponse)
async def search_comparables(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    address: Annotated[str, Query(min_length=1)],
    db: Annotated[Session, Depends(get_db)],
    time_period_months: Annotated[int, Query()] = 3,
    distance_miles: Annotated[float, Query()] = 1.0,
    same_schools: Annotated[bool, Query()] = True,
    sqft_pct: Annotated[int, Query(ge=0, le=40)] = 10,
    lot_pct: Annotated[int, Query(ge=0, le=40)] = 10,
    same_beds: Annotated[bool, Query()] = True,
    same_baths: Annotated[bool, Query()] = True,
    year_built_diff: Annotated[int, Query(ge=0, le=20)] = 10,
) -> ComparablesResponse:
    """Find comparable sold properties and rank by ML feature similarity."""
    # 1. Find subject property
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    subject = db.execute(
        select(RedfinListing)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .order_by(func.ST_Distance(RedfinListing.location, point))
        .limit(1)
    ).scalar_one_or_none()

    if subject is None:
        raise HTTPException(status_code=404, detail="Subject property not found")

    # 2. Get subject's school district for filtering
    subject_geo = db.execute(
        select(PropertyGeoLookup).where(PropertyGeoLookup.property_id == subject.id)
    ).scalar_one_or_none()

    # 3. Build candidate query
    cutoff = _months_ago(time_period_months)
    radius_m = distance_miles * METERS_PER_MILE

    stmt = select(RedfinListing.id).where(
        RedfinListing.id != subject.id,
        RedfinListing.location.isnot(None),
        RedfinListing.listing_status == "SOLD",
        RedfinListing.sold_date.isnot(None),
        RedfinListing.sold_date >= cutoff,
        ST_DWithin(
            cast(RedfinListing.location, Geography()),
            cast(point, Geography()),
            radius_m,
        ),
    )

    # School district filter
    if same_schools and subject_geo and subject_geo.school_district_geoid:
        stmt = stmt.join(
            PropertyGeoLookup, PropertyGeoLookup.property_id == RedfinListing.id
        ).where(PropertyGeoLookup.school_district_geoid == subject_geo.school_district_geoid)

    # Beds / baths filters
    if same_beds and subject.num_beds is not None:
        stmt = stmt.where(RedfinListing.num_beds == subject.num_beds)

    if same_baths and subject.num_baths is not None:
        stmt = stmt.where(RedfinListing.num_baths == subject.num_baths)

    # Sqft range
    if subject.sqft and sqft_pct > 0:
        lo = int(subject.sqft * (1 - sqft_pct / 100))
        hi = int(subject.sqft * (1 + sqft_pct / 100))
        stmt = stmt.where(or_(RedfinListing.sqft.between(lo, hi), RedfinListing.sqft.is_(None)))

    # Lot size range
    if subject.lot_size and lot_pct > 0:
        lo_lot = subject.lot_size * (1 - lot_pct / 100)
        hi_lot = subject.lot_size * (1 + lot_pct / 100)
        stmt = stmt.where(
            or_(RedfinListing.lot_size.between(lo_lot, hi_lot), RedfinListing.lot_size.is_(None))
        )

    # Year built range
    if subject.year_built and year_built_diff > 0:
        stmt = stmt.where(
            or_(
                RedfinListing.year_built.between(
                    subject.year_built - year_built_diff,
                    subject.year_built + year_built_diff,
                ),
                RedfinListing.year_built.is_(None),
            )
        )

    candidate_ids = [row[0] for row in db.execute(stmt).all()]
    total_candidates = len(candidate_ids)

    if not candidate_ids:
        # No candidates — return subject only
        subject_comp = _build_comp_property(subject, db)
        return ComparablesResponse(subject=subject_comp, comparables=[], total_candidates=0)

    # 4. Assemble feature matrix for subject + candidates
    all_ids = [subject.id] + candidate_ids
    try:
        feature_df = assemble_features(db, property_ids=all_ids)
    except Exception:
        logger.exception("Feature assembly failed, falling back to empty features")
        feature_df = None

    # 5. Find nearest comparables via NN
    top_comps: list[tuple[int, float]] = []
    if feature_df is not None and not feature_df.empty and subject.id in feature_df.index:
        top_comps = find_nearest_comparables(feature_df, subject.id, n=5)
    else:
        # Fallback: return candidates ordered by ID (no ranking)
        top_comps = [(cid, 0.0) for cid in candidate_ids[:5]]

    # 6. Build feature rows for display
    feature_rows: dict[int, dict] = {}
    if feature_df is not None and not feature_df.empty:
        for pid in [subject.id] + [c[0] for c in top_comps]:
            if pid in feature_df.index:
                row = feature_df.loc[pid]
                feature_rows[pid] = {
                    col: (None if hasattr(val, "__float__") and str(val) == "nan" else val)
                    for col, val in row.items()
                    if col not in ("sold_price", "census_tract_geoid")
                }

    # 7. Build response
    subject_comp = _build_comp_property(subject, db, feature_row=feature_rows.get(subject.id))

    comparables: list[CompProperty] = []
    comp_ids = [c[0] for c in top_comps]
    dist_map = dict(top_comps)

    if comp_ids:
        comp_listings = (
            db.execute(select(RedfinListing).where(RedfinListing.id.in_(comp_ids))).scalars().all()
        )
        listing_map = {p.id: p for p in comp_listings}

        for cid in comp_ids:
            prop = listing_map.get(cid)
            if prop:
                comparables.append(
                    _build_comp_property(
                        prop,
                        db,
                        feature_row=feature_rows.get(cid),
                        similarity_distance=round(dist_map[cid], 4),
                    )
                )

    return ComparablesResponse(
        subject=subject_comp,
        comparables=comparables,
        total_candidates=total_candidates,
    )
