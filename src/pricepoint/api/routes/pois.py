"""Points of interest endpoint — real PostGIS spatial queries."""

import hashlib
import json
import logging
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y, ST_Centroid, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import String, case, cast, func, literal, or_, select, text, union_all
from sqlalchemy.orm import Session

from pricepoint.api.auth import get_current_user
from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.pois import (
    PoiAutocompleteItem,
    PoiAutocompleteResponse,
    PointOfInterest,
    PoisMetrics,
    PoisResponse,
    PoisSearchResponse,
    SavedPoiMatch,
    SavedPoiNearbyGroup,
    SavedPoiNearbyResponse,
)
from pricepoint.db.models import (
    Hospital,
    Place,
    PlaceName,
    SavedPoi,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pois"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 604800  # 7 days


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, Geography()),
        cast(point, Geography()),
        radius_meters,
    )


def _distance_miles(geom_col, point):  # noqa: ANN001, ANN201
    """Compute distance in miles between a geometry column and a point."""
    return (
        func.ST_Distance(
            cast(geom_col, Geography()),
            cast(point, Geography()),
        )
        / METERS_PER_MILE
    )


# Table config: (model_class, name_column_attr, category, geom_needs_centroid)
_POI_TABLES: list[tuple] = [
    (Hospital, "name", "Healthcare", False),
]

# Map Overture Place categories to dashboard categories
_OVERTURE_CATEGORY_MAP: dict[str, str] = {
    "grocery": "Grocery",
    "supermarket": "Grocery",
    "health_and_medical": "Healthcare",
    "pharmacy": "Healthcare",
    "active_life": "Recreation",
    "fitness": "Recreation",
    "parks": "Recreation",
    "eat_and_drink": "Dining",
    "restaurant": "Dining",
    "cafe": "Dining",
    "retail": "Shopping",
    "shopping": "Shopping",
    "professional_services": "Services",
    "financial": "Services",
    "automotive": "Services",
}

_DASHBOARD_CATEGORIES = {"Grocery", "Healthcare", "Recreation", "Dining", "Shopping", "Services"}


def _map_overture_category(raw_category: str | None) -> str | None:
    """Map an Overture Place category string to a dashboard category."""
    if not raw_category:
        return None
    lower = raw_category.lower()
    # Try exact match first
    if lower in _OVERTURE_CATEGORY_MAP:
        return _OVERTURE_CATEGORY_MAP[lower]
    # Try prefix match (e.g. "eat_and_drink/restaurant" matches "eat_and_drink")
    for key, dashboard_cat in _OVERTURE_CATEGORY_MAP.items():
        if lower.startswith(key) or key in lower:
            return dashboard_cat
    return None


def _build_poi_query(property_point, radius_meters: float):  # noqa: ANN001, ANN201
    """Build a UNION ALL query across hospital POI tables."""
    queries = []
    for model, name_attr, category, needs_centroid in _POI_TABLES:
        geom_col = model.geom
        # For MULTIPOLYGON, use centroid for point operations
        point_geom = ST_Centroid(geom_col) if needs_centroid else geom_col

        q = select(
            cast(model.id, String).label("poi_id"),
            getattr(model, name_attr).label("poi_name"),
            literal(category).label("category"),
            literal(None).label("subcategory"),
            literal(None).label("address"),
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


def _cache_key(lat: float, lon: float, radius_miles: float, per_category: int = 5) -> str:
    """Build a deterministic cache key for the POI query."""
    raw = f"pois:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}:{per_category}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"pois:{digest}"


def _query_places(
    db: Session,
    property_point,  # noqa: ANN001
    radius_meters: float,
    per_category: int,
) -> list[PointOfInterest]:
    """Query the Place table for commercial POIs, mapped to dashboard categories."""
    stmt = (
        select(
            cast(Place.id, String).label("poi_id"),
            Place.name.label("poi_name"),
            Place.category.label("raw_category"),
            Place.address.label("address"),
            ST_Y(Place.geom).label("lat"),
            ST_X(Place.geom).label("lon"),
            _distance_miles(Place.geom, property_point).label("distance_miles"),
        )
        .where(
            Place.geom.isnot(None),
            _st_dwithin_geography(Place.geom, property_point, radius_meters),
        )
        .order_by(text("distance_miles"))
    )
    rows = db.execute(stmt).all()

    # Bucket by dashboard category, keep top N per category
    buckets: dict[str, list[PointOfInterest]] = {cat: [] for cat in _DASHBOARD_CATEGORIES}
    for row in rows:
        dashboard_cat = _map_overture_category(row.raw_category)
        if dashboard_cat is None:
            continue
        bucket = buckets[dashboard_cat]
        if len(bucket) >= per_category:
            continue
        dist = round(row.distance_miles, 2) if row.distance_miles is not None else 0.0
        bucket.append(
            PointOfInterest(
                id=f"OVERTURE-{row.poi_id}",
                name=row.poi_name or "Unknown",
                category=dashboard_cat,
                subcategory=row.raw_category,
                address=row.address,
                lat=round(row.lat, 6) if row.lat is not None else 0.0,
                lon=round(row.lon, 6) if row.lon is not None else 0.0,
                distance_miles=dist,
                drive_minutes=max(1, round(dist * 3)),
            )
        )

    result: list[PointOfInterest] = []
    for pois_list in buckets.values():
        result.extend(pois_list)
    result.sort(key=lambda p: p.distance_miles)
    return result


@router.get("/pois", response_model=PoisResponse)
async def get_pois(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2.0,
    per_category: Annotated[int, Query(ge=1, le=20)] = 5,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> PoisResponse:
    """Return points of interest near the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles, per_category)
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

    # Hospital-based POIs
    cte = _build_poi_query(property_point, radius_meters)

    rows = db.execute(
        select(
            cte.c.poi_id,
            cte.c.poi_name,
            cte.c.category,
            cte.c.subcategory,
            cte.c.address,
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
                subcategory=row.subcategory,
                address=row.address,
                lat=round(row.lat, 6) if row.lat is not None else 0.0,
                lon=round(row.lon, 6) if row.lon is not None else 0.0,
                distance_miles=dist,
                drive_minutes=drive_min,
            )
        )

    # Place-based (Overture) POIs
    place_pois = _query_places(db, property_point, radius_meters, per_category)
    for p in place_pois:
        if nearest_dist is None or p.distance_miles < nearest_dist:
            nearest_dist = p.distance_miles
        categories.add(p.category)
    pois.extend(place_pois)
    pois.sort(key=lambda p: p.distance_miles)

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
        .order_by(text("distance_miles"))
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


@router.get("/pois/autocomplete", response_model=PoiAutocompleteResponse)
def autocomplete_pois(
    q: Annotated[str, Query(min_length=2, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> PoiAutocompleteResponse:
    """Autocomplete POI brands/names for saving."""
    pattern = f"%{q.strip()}%"

    stmt = (
        select(
            PlaceName.match_type,
            PlaceName.value,
            PlaceName.category,
            PlaceName.count.label("place_count"),
        )
        .where(PlaceName.value.ilike(pattern))
        .order_by(
            case((PlaceName.match_type == "brand", 0), else_=1),
            PlaceName.count.desc(),
        )
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    results = [
        PoiAutocompleteItem(
            match_type=r.match_type,
            match_value=r.value,
            display_name=r.value,
            category=r.category,
            count=r.place_count,
        )
        for r in rows
    ]

    return PoiAutocompleteResponse(results=results, query=q)


DEDUP_RADIUS_METERS = 100


def _deduplicate_matches(matches: list[SavedPoiMatch], ref_lat: float) -> list[SavedPoiMatch]:
    """Keep only the nearest match from each spatial cluster."""
    if len(matches) <= 1:
        return matches
    cos_lat = math.cos(math.radians(ref_lat))
    kept: list[SavedPoiMatch] = []
    for m in matches:
        is_dup = False
        for k in kept:
            dlat = abs(m.lat - k.lat) * 111_000
            dlon = abs(m.lon - k.lon) * 111_000 * cos_lat
            if (dlat * dlat + dlon * dlon) < DEDUP_RADIUS_METERS**2:
                is_dup = True
                break
        if not is_dup:
            kept.append(m)
    return kept


@router.get("/pois/saved-nearby", response_model=SavedPoiNearbyResponse)
def get_saved_pois_nearby(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=50)] = 10.0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    user: Annotated[User, Depends(get_current_user)] = None,  # type: ignore[assignment]
) -> SavedPoiNearbyResponse:
    """Return nearby locations matching the user's saved POIs."""
    saved = db.execute(select(SavedPoi).where(SavedPoi.user_id == user.id)).scalars().all()

    if not saved:
        return SavedPoiNearbyResponse(groups=[])

    # Build expanded lookup maps that include alternate names
    brand_lookup: dict[str, SavedPoi] = {}
    name_lookup: dict[str, SavedPoi] = {}
    for s in saved:
        all_values = [s.match_value] + (s.alternate_names or [])
        lookup = brand_lookup if s.match_type == "brand" else name_lookup
        for v in all_values:
            lookup[v] = s

    radius_meters = radius_miles * METERS_PER_MILE
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    or_conditions = []
    if brand_lookup:
        or_conditions.append(Place.brand_name.in_(list(brand_lookup.keys())))
    if name_lookup:
        or_conditions.append(Place.name.in_(list(name_lookup.keys())))

    stmt = (
        select(
            cast(Place.id, String).label("poi_id"),
            Place.name.label("poi_name"),
            Place.brand_name,
            Place.address,
            Place.category,
            ST_Y(Place.geom).label("lat"),
            ST_X(Place.geom).label("lon"),
            _distance_miles(Place.geom, property_point).label("distance_miles"),
        )
        .where(
            Place.geom.isnot(None),
            _st_dwithin_geography(Place.geom, property_point, radius_meters),
            or_(*or_conditions),
        )
        .order_by(text("distance_miles"))
    )
    rows = db.execute(stmt).all()

    # Group rows by saved POI
    groups_map: dict[int, list[SavedPoiMatch]] = {s.id: [] for s in saved}
    for row in rows:
        matched_poi: SavedPoi | None = None
        if row.brand_name and row.brand_name in brand_lookup:
            matched_poi = brand_lookup[row.brand_name]
        elif row.poi_name and row.poi_name in name_lookup:
            matched_poi = name_lookup[row.poi_name]
        if matched_poi is None:
            continue
        dist = round(row.distance_miles, 2) if row.distance_miles else 0.0
        groups_map[matched_poi.id].append(
            SavedPoiMatch(
                id=f"SAVED-{row.poi_id}",
                name=row.poi_name or "Unknown",
                address=row.address,
                lat=round(row.lat, 6) if row.lat else 0.0,
                lon=round(row.lon, 6) if row.lon else 0.0,
                distance_miles=dist,
                drive_minutes=max(1, round(dist * 3)),
            )
        )

    # Deduplicate nearby matches within each group
    for poi_id in groups_map:
        groups_map[poi_id] = _deduplicate_matches(groups_map[poi_id], lat)

    groups = [
        SavedPoiNearbyGroup(
            saved_poi_id=s.id,
            display_name=s.display_name,
            category=s.category,
            match_type=s.match_type,
            matches=groups_map[s.id],
            user_category=s.user_category,
            marker_color=s.marker_color,
            marker_image_url=s.marker_image_url,
        )
        for s in saved
        if groups_map[s.id]
    ]
    return SavedPoiNearbyResponse(groups=groups)
