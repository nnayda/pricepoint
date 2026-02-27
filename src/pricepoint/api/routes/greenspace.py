"""Greenspace endpoint — returns parks and trails from PostGIS spatial queries."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y, ST_DWithin, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, literal, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.greenspace import (
    GreenspaceFeature,
    GreenspaceMetrics,
    GreenspaceResponse,
)
from pricepoint.db.models import (
    BlockGroup,
    Greenspace,
    GreenspaceRegionMetric,
    PropertyGeoLookup,
    RedfinListing,
    Trail,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["greenspace"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, Geography()),
        cast(point, Geography()),
        radius_meters,
    )


def _st_distance_geography(geom_col, point):  # noqa: ANN001, ANN201
    """ST_Distance using geography cast for meter-based distance."""
    return func.ST_Distance(
        cast(geom_col, Geography()),
        cast(point, Geography()),
    )


def _build_greenways_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a query for trails from the USGS National Digital Trails table."""
    trails_q = select(
        cast(Trail.id, String).label("feature_id"),
        func.coalesce(Trail.name, "Unknown Trail").label("name"),
        literal("trail").label("feature_type"),
        ST_Y(func.ST_Centroid(Trail.geom)).label("lat"),
        ST_X(func.ST_Centroid(Trail.geom)).label("lon"),
        (_st_distance_geography(Trail.geom, property_point) / METERS_PER_MILE).label(
            "distance_miles"
        ),
        literal("usgs").label("source"),
    ).where(
        Trail.geom.isnot(None),
        _st_dwithin_geography(Trail.geom, property_point, radius_meters),
    )

    return trails_q.cte("all_greenways")


def _build_parks_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a query for greenspaces from the PAD-US table."""
    parks_q = select(
        cast(Greenspace.id, String).label("feature_id"),
        func.coalesce(Greenspace.name, "Unknown Park").label("name"),
        literal("park").label("feature_type"),
        ST_Y(func.ST_Centroid(Greenspace.geom)).label("lat"),
        ST_X(func.ST_Centroid(Greenspace.geom)).label("lon"),
        (_st_distance_geography(Greenspace.geom, property_point) / METERS_PER_MILE).label(
            "distance_miles"
        ),
        Greenspace.gis_acres.label("acreage"),
        literal("padus").label("source"),
    ).where(
        Greenspace.geom.isnot(None),
        _st_dwithin_geography(Greenspace.geom, property_point, radius_meters),
    )

    return parks_q.cte("all_parks")


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

    # Query parks (PAD-US greenspaces)
    parks_cte = _build_parks_query(property_point, radius_meters)
    park_rows = db.execute(
        select(
            parks_cte.c.feature_id,
            parks_cte.c.name,
            parks_cte.c.feature_type,
            parks_cte.c.lat,
            parks_cte.c.lon,
            parks_cte.c.distance_miles,
            parks_cte.c.acreage,
            parks_cte.c.source,
        ).order_by(parks_cte.c.distance_miles)
    ).all()

    # Query greenways (trails)
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

    for row in park_rows:
        if row.lat is not None and row.lon is not None:
            features.append(
                GreenspaceFeature(
                    id=f"park-{row.source}-{row.feature_id}",
                    name=row.name,
                    feature_type="park",
                    lat=round(row.lat, 6),
                    lon=round(row.lon, 6),
                    distance_miles=round(row.distance_miles, 2),
                    acreage=round(row.acreage, 1) if row.acreage else None,
                )
            )

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

    # Compute park metrics from PAD-US data
    parks_within_1mi_rows = [r for r in park_rows if r.distance_miles <= 1.0]
    parks_within_1mi = len(parks_within_1mi_rows)
    nearest_park_miles = round(park_rows[0].distance_miles, 2) if park_rows else 0.0
    total_green_acres_1mi = round(sum(r.acreage or 0.0 for r in parks_within_1mi_rows), 1)

    nearest_greenway_miles = (
        round(min(row.distance_miles for row in greenway_rows), 2) if greenway_rows else 0.0
    )

    # Look up precomputed z-score from block group containing this point
    greenspace_z = 0.0
    try:
        # Try precomputed geo lookup first
        bg_geoid = db.execute(
            select(PropertyGeoLookup.census_block_group_geoid)
            .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
            .where(
                RedfinListing.location.isnot(None),
                ST_DWithin(RedfinListing.location, property_point, 0.001),
            )
            .limit(1)
        ).scalar_one_or_none()

        if bg_geoid is None:
            # Fallback: spatial containment for unlisted addresses
            bg_row = db.execute(
                select(BlockGroup.geoid).where(func.ST_Contains(BlockGroup.geom, property_point))
            ).first()
            if bg_row is not None:
                bg_geoid = bg_row.geoid

        if bg_geoid is not None:
            metric_row = db.execute(
                select(GreenspaceRegionMetric.greenspace_ratio_zscore).where(
                    GreenspaceRegionMetric.geo_level == "block_group",
                    GreenspaceRegionMetric.geoid == bg_geoid,
                )
            ).first()
            if metric_row is not None and metric_row.greenspace_ratio_zscore is not None:
                greenspace_z = round(metric_row.greenspace_ratio_zscore, 2)
    except Exception:
        logger.warning("Failed to look up greenspace z-score", exc_info=True)

    metrics = GreenspaceMetrics(
        parks_within_1mi=parks_within_1mi,
        nearest_park_miles=nearest_park_miles,
        nearest_greenway_miles=nearest_greenway_miles,
        total_green_acres_1mi=total_green_acres_1mi,
        greenspace_z_score=greenspace_z,
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
