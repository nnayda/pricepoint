"""Schools endpoint — returns nearby schools via spatial proximity."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_Contains,
    ST_DWithin,
    ST_MakePoint,
    ST_SetSRID,
    ST_Simplify,
)
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.property import SchoolDistrictInfo, SchoolNearby, SchoolsNearbyResponse
from pricepoint.db.models import (
    PropertyGeoLookup,
    PropertySchool,
    RedfinListing,
    School,
    SchoolDistrict,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schools"])

_MILES_TO_METERS = 1609.344
# Approximate degree-per-mile at mid-latitudes (~35-40°N) for fast geometry queries.
# 1 degree latitude ≈ 69 miles; using a slightly generous factor for longitude.
_MILES_TO_DEGREES = 1.0 / 69.0
# Tolerance for ST_Simplify on district boundaries (in degrees, ~111m)
_DISTRICT_SIMPLIFY_TOLERANCE = 0.001


@router.get("/schools/nearby", response_model=SchoolsNearbyResponse)
async def get_nearby_schools(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
    radius_miles: Annotated[float, Query(gt=0, le=50)] = 25.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SchoolsNearbyResponse:
    """Return schools near a given location, ordered by distance.

    Uses a spatial query on the schools table (gold layer).
    If a property is found at the given coordinates, enriches results
    with assigned status and travel times from the property_schools linkage.
    Also returns school district boundaries near the property.
    """
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    radius_meters = radius_miles * _MILES_TO_METERS

    # Distance in metres via geography cast for accuracy
    geo = Geography()
    dist_col = func.ST_Distance(
        cast(School.location, geo),
        cast(point, geo),
    ).label("distance_m")

    stmt = (
        select(
            School,
            dist_col,
            func.ST_Y(School.location).label("school_lat"),
            func.ST_X(School.location).label("school_lon"),
        )
        .where(
            School.location.isnot(None),
            ST_DWithin(
                cast(School.location, geo),
                cast(point, geo),
                radius_meters,
            ),
        )
        .order_by(dist_col)
        .limit(limit)
    )

    rows = db.execute(stmt).all()

    # Try to get home district geoid from precomputed lookup
    home_district_geoid: str | None = db.execute(
        select(PropertyGeoLookup.school_district_geoid)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    # Query school districts using geometry bounding-box filter (much faster than
    # geography cast on complex MULTIPOLYGON boundaries).  ST_Expand + ST_DWithin
    # in geometry mode leverages the GiST index efficiently.
    radius_degrees = radius_miles * _MILES_TO_DEGREES
    simplified = ST_Simplify(SchoolDistrict.geom, _DISTRICT_SIMPLIFY_TOLERANCE)
    geojson_col = ST_AsGeoJSON(simplified).label("geojson")

    if home_district_geoid:
        # Use precomputed geoid to determine home district
        is_home_expr = (SchoolDistrict.geoid == home_district_geoid).label("is_home")
    else:
        # Fallback: spatial containment check
        is_home_expr = ST_Contains(SchoolDistrict.geom, point).label("is_home")

    district_stmt = select(SchoolDistrict, is_home_expr, geojson_col).where(
        ST_DWithin(SchoolDistrict.geom, point, radius_degrees)
    )
    district_rows = db.execute(district_stmt).all()

    home_district_id: int | None = None
    school_districts: list[SchoolDistrictInfo] = []
    for district, is_home, geojson_str in district_rows:
        if is_home:
            home_district_id = district.id
        geojson = json.loads(geojson_str) if geojson_str else None
        label_lat = float(district.intptlat) if district.intptlat else None
        label_lon = float(district.intptlon) if district.intptlon else None
        school_districts.append(
            SchoolDistrictInfo(
                name=district.name,
                geoid=district.geoid,
                district_type=district.district_type,
                geojson=geojson,
                is_home=bool(is_home),
                label_lat=label_lat,
                label_lon=label_lon,
            )
        )

    # Try to find a property at this location for linkage enrichment
    tolerance = 0.001  # ~111 m
    prop = db.execute(
        select(RedfinListing)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, tolerance),
        )
        .limit(1)
    ).scalar_one_or_none()

    # Build a lookup of PropertySchool linkage data if property exists
    linkage: dict[int, PropertySchool] = {}
    if prop:
        links = (
            db.execute(select(PropertySchool).where(PropertySchool.property_id == prop.id))
            .scalars()
            .all()
        )
        linkage = {link.school_id: link for link in links}

    schools: list[SchoolNearby] = []
    for school, distance_m, school_lat, school_lon in rows:
        # Build address
        addr_parts = [p for p in [school.street, school.city, school.state, school.zip_code] if p]
        address = ", ".join(addr_parts) if addr_parts else None

        distance_miles = distance_m / _MILES_TO_METERS

        # Enrich with linkage data if available
        link = linkage.get(school.id)
        assigned = link.assigned if link else False
        drive_minutes = link.drive_minutes if link and link.drive_minutes else 0
        walk_minutes = link.walk_minutes if link else None
        # Prefer linkage distance if available (more accurate via OSRM)
        if link and link.distance_miles:
            distance_miles = link.distance_miles

        # Determine if school is in the same district
        in_district = bool(
            home_district_id and school.district_id and school.district_id == home_district_id
        )

        schools.append(
            SchoolNearby(
                name=school.name,
                address=address,
                school_type=school.school_type or "Unknown",
                school_level=school.school_level,
                rating=(
                    int(school.rating) if school.rating is not None and school.rating > 0 else None
                ),
                grades=school.grades,
                distance_miles=round(distance_miles, 1),
                drive_minutes=drive_minutes,
                walk_minutes=walk_minutes,
                student_teacher_ratio=school.student_teacher_ratio,
                enrollment=school.enrollment,
                assigned=assigned,
                lat=school_lat,
                lon=school_lon,
                pct_frl_eligible=school.pct_frl_eligible,
                in_district=in_district,
            )
        )

    return SchoolsNearbyResponse(schools=schools, school_districts=school_districts)
