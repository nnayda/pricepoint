"""Points of interest endpoint — real PostGIS spatial queries."""

import hashlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_X, ST_Y, ST_Centroid, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import String, cast, func, literal, select, text, union_all
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.pois import (
    PointOfInterest,
    PoisMetrics,
    PoisResponse,
    PoisSearchResponse,
)
from pricepoint.db.models import (
    Hospital,
    Place,
    WakeFarmersMarket,
    WakeLibrary,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pois"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, text("geography")),
        cast(point, text("geography")),
        radius_meters,
    )


def _distance_miles(geom_col, point):  # noqa: ANN001, ANN201
    """Compute distance in miles between a geometry column and a point."""
    return (
        func.ST_Distance(
            cast(geom_col, text("geography")),
            cast(point, text("geography")),
        )
        / METERS_PER_MILE
    )


# Table config: (model_class, name_column_attr, category, geom_needs_centroid)
_POI_TABLES: list[tuple] = [
    (WakeFarmersMarket, "name", "grocery", False),
    (WakeLibrary, "name", "library", False),
    (Hospital, "name", "medical", False),
]


def _build_poi_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a UNION ALL query across all 3 POI tables."""
    queries = []
    for model, name_attr, category, needs_centroid in _POI_TABLES:
        geom_col = model.geom
        # For MULTIPOLYGON, use centroid for point operations
        point_geom = ST_Centroid(geom_col) if needs_centroid else geom_col

        q = select(
            cast(model.id, String).label("poi_id"),
            getattr(model, name_attr).label("poi_name"),
            literal(category).label("category"),
            ST_Y(point_geom).label("lat"),
            ST_X(point_geom).label("lon"),
            _distance_miles(point_geom, property_point).label("distance_miles"),
        ).where(
            geom_col.isnot(None),
            _st_dwithin_geography(
                point_geom if not needs_centroid else geom_col,
                property_point,
                radius_meters,
            ),
        )
        queries.append(q)

    return union_all(*queries).cte("all_pois")


def _cache_key(lat: float, lon: float, radius_miles: float) -> str:
    """Build a deterministic cache key for the POI query."""
    raw = f"pois:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"pois:{digest}"


@router.get("/pois", response_model=PoisResponse)
async def get_pois(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> PoisResponse:
    """Return points of interest near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return PoisResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    cte = _build_poi_query(property_point, radius_meters)

    rows = db.execute(
        select(
            cte.c.poi_id,
            cte.c.poi_name,
            cte.c.category,
            cte.c.lat,
            cte.c.lon,
            cte.c.distance_miles,
        ).order_by(cte.c.distance_miles)
    ).all()

    pois: list[PointOfInterest] = []
    categories: set[str] = set()
    nearest_dist: float | None = None

    for row in rows:
        dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0
        drive_min = max(1, round(dist * 3))
        category = row.category or "other"

        if nearest_dist is None or dist < nearest_dist:
            nearest_dist = dist
        categories.add(category)

        pois.append(
            PointOfInterest(
                id=f"{category.upper()}-{row.poi_id}",
                name=row.poi_name or "Unknown",
                category=category,
                lat=round(row.lat, 6) if row.lat is not None else 0.0,
                lon=round(row.lon, 6) if row.lon is not None else 0.0,
                distance_miles=dist,
                drive_minutes=drive_min,
            )
        )

    metrics = PoisMetrics(
        total_count=len(pois),
        categories_represented=len(categories),
        nearest_distance_miles=round(nearest_dist, 2) if nearest_dist is not None else None,
    )

    response = PoisResponse(pois=pois, metrics=metrics)

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


def _search_cache_key(lat: float, lon: float, query: str, radius_miles: float) -> str:
    """Build a deterministic cache key for POI search."""
    raw = f"poi-search:{lat:.6f}:{lon:.6f}:{query.lower().strip()}:{radius_miles:.2f}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"poi-search:{digest}"


@router.get("/pois/search", response_model=PoisSearchResponse)
async def search_pois(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    query: Annotated[str, Query(min_length=1, max_length=200)],
    radius_miles: Annotated[float, Query(gt=0, le=50)] = 5.0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> PoisSearchResponse:
    """Search for commercial POIs by name or category near a location."""
    c_key = _search_cache_key(lat, lon, query, radius_miles)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return PoisSearchResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    radius_meters = radius_miles * METERS_PER_MILE
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    search_pattern = f"%{query.strip()}%"

    stmt = (
        select(
            cast(Place.id, String).label("poi_id"),
            Place.name.label("poi_name"),
            Place.category.label("category"),
            Place.brand_name.label("brand_name"),
            Place.address.label("address"),
            Place.phone.label("phone"),
            ST_Y(Place.geom).label("lat"),
            ST_X(Place.geom).label("lon"),
            _distance_miles(Place.geom, property_point).label("distance_miles"),
        )
        .where(
            Place.geom.isnot(None),
            _st_dwithin_geography(Place.geom, property_point, radius_meters),
            (Place.name.ilike(search_pattern) | Place.category.ilike(search_pattern)),
        )
        .order_by(literal("distance_miles"))
        .limit(limit)
    )

    rows = db.execute(stmt).all()

    pois: list[PointOfInterest] = []
    for row in rows:
        dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0
        drive_min = max(1, round(dist * 3))
        pois.append(
            PointOfInterest(
                id=f"OVERTURE-{row.poi_id}",
                name=row.poi_name or "Unknown",
                category=row.category or "other",
                lat=round(row.lat, 6) if row.lat is not None else 0.0,
                lon=round(row.lon, 6) if row.lon is not None else 0.0,
                distance_miles=dist,
                drive_minutes=drive_min,
            )
        )

    response = PoisSearchResponse(pois=pois, total_count=len(pois), query=query)

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
