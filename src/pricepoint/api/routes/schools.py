"""Schools endpoint — returns nearby schools via spatial proximity."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.property import SchoolNearby
from pricepoint.db.models import PropertySchool, RedfinListing, School

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schools"])

_MILES_TO_METERS = 1609.344


@router.get("/schools/nearby", response_model=list[SchoolNearby])
async def get_nearby_schools(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
    radius_miles: Annotated[float, Query(gt=0, le=50)] = 10.0,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[SchoolNearby]:
    """Return schools near a given location, ordered by distance.

    Uses a spatial query on the schools table (gold layer).
    If a property is found at the given coordinates, enriches results
    with assigned status and travel times from the property_schools linkage.
    """
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    radius_meters = radius_miles * _MILES_TO_METERS

    # Distance in metres via geography cast for accuracy
    dist_col = func.ST_Distance(
        func.cast(School.location, func.geography),
        func.cast(point, func.geography),
    ).label("distance_m")

    stmt = (
        select(School, dist_col)
        .where(
            School.location.isnot(None),
            ST_DWithin(
                func.cast(School.location, func.geography),
                func.cast(point, func.geography),
                radius_meters,
            ),
        )
        .order_by(dist_col)
        .limit(limit)
    )

    rows = db.execute(stmt).all()

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
    for school, distance_m in rows:
        # Build address
        addr_parts = [p for p in [school.street, school.city, school.state, school.zip_code] if p]
        address = ", ".join(addr_parts) if addr_parts else None

        # Extract lat/lon from geometry
        school_lat: float | None = None
        school_lon: float | None = None
        if school.location is not None:
            coords = db.execute(
                select(
                    func.ST_Y(school.location).label("lat"),
                    func.ST_X(school.location).label("lon"),
                )
            ).one()
            school_lat = coords.lat
            school_lon = coords.lon

        distance_miles = distance_m / _MILES_TO_METERS

        # Enrich with linkage data if available
        link = linkage.get(school.id)
        assigned = link.assigned if link else False
        drive_minutes = link.drive_minutes if link and link.drive_minutes else 0
        walk_minutes = link.walk_minutes if link else None
        # Prefer linkage distance if available (more accurate via OSRM)
        if link and link.distance_miles:
            distance_miles = link.distance_miles

        schools.append(
            SchoolNearby(
                name=school.name,
                address=address,
                school_type=school.school_type or "Unknown",
                school_level=school.school_level,
                rating=int(school.rating) if school.rating else 0,
                grades=school.grades,
                distance_miles=round(distance_miles, 1),
                drive_minutes=drive_minutes,
                walk_minutes=walk_minutes,
                student_teacher_ratio=school.student_teacher_ratio,
                enrollment=school.enrollment,
                assigned=assigned,
                lat=school_lat,
                lon=school_lon,
            )
        )

    return schools
