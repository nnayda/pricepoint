"""Greenspace endpoint — returns trails from PostGIS spatial queries."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_X, ST_Y, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, literal, select, text, union_all
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.greenspace import (
    GreenspaceFeature,
    GreenspaceMetrics,
    GreenspaceResponse,
)
from pricepoint.db.models import (
    CaryGreenway,
    RaleighGreenway,
    WakeGreenway,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["greenspace"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, text("geography")),
        cast(point, text("geography")),
        radius_meters,
    )


def _st_distance_geography(geom_col, point):  # noqa: ANN001, ANN201
    """ST_Distance using geography cast for meter-based distance."""
    return func.ST_Distance(
        cast(geom_col, text("geography")),
        cast(point, text("geography")),
    )


def _build_greenways_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a union query across all three greenway tables."""
    # WakeGreenway: MULTILINESTRING, trail_name
    wake_q = select(
        cast(WakeGreenway.id, String).label("feature_id"),
        func.coalesce(WakeGreenway.trail_name, "Unknown Trail").label("name"),
        literal("trail").label("feature_type"),
        ST_Y(func.ST_Centroid(WakeGreenway.geom)).label("lat"),
        ST_X(func.ST_Centroid(WakeGreenway.geom)).label("lon"),
        (_st_distance_geography(WakeGreenway.geom, property_point) / METERS_PER_MILE).label(
            "distance_miles"
        ),
        literal("wake").label("source"),
    ).where(
        WakeGreenway.geom.isnot(None),
        _st_dwithin_geography(WakeGreenway.geom, property_point, radius_meters),
    )

    # RaleighGreenway: MULTILINESTRING, trail_name
    raleigh_q = select(
        cast(RaleighGreenway.id, String).label("feature_id"),
        func.coalesce(RaleighGreenway.trail_name, "Unknown Trail").label("name"),
        literal("trail").label("feature_type"),
        ST_Y(func.ST_Centroid(RaleighGreenway.geom)).label("lat"),
        ST_X(func.ST_Centroid(RaleighGreenway.geom)).label("lon"),
        (_st_distance_geography(RaleighGreenway.geom, property_point) / METERS_PER_MILE).label(
            "distance_miles"
        ),
        literal("raleigh").label("source"),
    ).where(
        RaleighGreenway.geom.isnot(None),
        _st_dwithin_geography(RaleighGreenway.geom, property_point, radius_meters),
    )

    # CaryGreenway: MULTILINESTRING, name
    cary_q = select(
        cast(CaryGreenway.id, String).label("feature_id"),
        func.coalesce(CaryGreenway.name, "Unknown Trail").label("name"),
        literal("trail").label("feature_type"),
        ST_Y(func.ST_Centroid(CaryGreenway.geom)).label("lat"),
        ST_X(func.ST_Centroid(CaryGreenway.geom)).label("lon"),
        (_st_distance_geography(CaryGreenway.geom, property_point) / METERS_PER_MILE).label(
            "distance_miles"
        ),
        literal("cary").label("source"),
    ).where(
        CaryGreenway.geom.isnot(None),
        _st_dwithin_geography(CaryGreenway.geom, property_point, radius_meters),
    )

    return union_all(wake_q, raleigh_q, cary_q).cte("all_greenways")


def _cache_key(lat: float, lon: float, radius_miles: float) -> str:
    """Build a deterministic cache key for the greenspace query."""
    raw = f"greenspace:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"greenspace:{digest}"


@router.get("/greenspace", response_model=GreenspaceResponse)
async def get_greenspace(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> GreenspaceResponse:
    """Return greenspace features and metrics near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return GreenspaceResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE

    # Build geography point
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query greenways
    greenways_cte = _build_greenways_query(property_point, radius_meters)
    greenway_rows = db.execute(
        select(
            greenways_cte.c.feature_id,
            greenways_cte.c.name,
            greenways_cte.c.feature_type,
            greenways_cte.c.lat,
            greenways_cte.c.lon,
            greenways_cte.c.distance_miles,
            greenways_cte.c.source,
        ).order_by(greenways_cte.c.distance_miles)
    ).all()

    # Build features list
    features: list[GreenspaceFeature] = []

    for row in greenway_rows:
        if row.lat is not None and row.lon is not None:
            features.append(
                GreenspaceFeature(
                    id=f"trail-{row.source}-{row.feature_id}",
                    name=row.name,
                    feature_type="trail",
                    lat=round(row.lat, 6),
                    lon=round(row.lon, 6),
                    distance_miles=round(row.distance_miles, 2),
                    acreage=None,
                )
            )

    # Sort all features by distance
    features.sort(key=lambda f: f.distance_miles)

    # Park metrics default to 0 (parks removed — will be re-added via gold tables)
    parks_within_1mi = 0
    nearest_park_miles = 0.0
    total_green_acres_1mi = 0.0

    nearest_greenway_miles = (
        round(min(row.distance_miles for row in greenway_rows), 2) if greenway_rows else 0.0
    )

    metrics = GreenspaceMetrics(
        parks_within_1mi=parks_within_1mi,
        nearest_park_miles=nearest_park_miles,
        nearest_greenway_miles=nearest_greenway_miles,
        total_green_acres_1mi=total_green_acres_1mi,
        greenspace_z_score=0.0,
    )

    response = GreenspaceResponse(features=features, metrics=metrics)

    # Write to cache
    if valkey is not None:
        try:
            await valkey.set(
                c_key,
                json.dumps(response.model_dump()),
                ex=CACHE_TTL,
            )
        except Exception:
            logger.warning("Valkey write failed for key %s", c_key, exc_info=True)

    return response
