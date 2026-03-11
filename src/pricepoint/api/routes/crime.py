"""Crime endpoint — returns crime data from the gold police_incidents table."""

import hashlib
import json
import logging
import math
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.crime import (
    CrimeHeatmapPoint,
    CrimeIncident,
    CrimeMetrics,
    CrimeResponse,
)
from pricepoint.db.models import PoliceIncident

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crime"])

METERS_PER_MILE = 1609.344
CACHE_TTL = 21600  # 6 hours

# Categories considered "violent" for violent_pct calculation
VIOLENT_KEYWORDS = {
    "assault",
    "homicide",
    "murder",
    "robbery",
    "rape",
    "kidnapping",
    "manslaughter",
    "violent",
    "weapon",
    "arson",
}


def _st_dwithin_geography(geom_col, point, radius_meters: float):  # noqa: ANN001, ANN201
    """ST_DWithin using geography cast for meter-based distance."""
    return func.ST_DWithin(
        cast(geom_col, Geography()),
        cast(point, Geography()),
        radius_meters,
    )


def _compute_intensity(occurred_at: datetime | date, now: datetime, days_back: int) -> float:
    """Compute heatmap intensity using exponential decay on recency.

    More recent incidents get higher intensity (closer to 1.0).
    Half-life is set to days_back / 4 so a quarter-period-old incident
    has intensity ~0.5.
    """
    if isinstance(occurred_at, date) and not isinstance(occurred_at, datetime):
        occurred_at = datetime(occurred_at.year, occurred_at.month, occurred_at.day, tzinfo=UTC)
    age_days = (now - occurred_at).total_seconds() / 86400.0
    half_life = max(days_back / 4.0, 1.0)
    intensity = math.exp(-0.693 * age_days / half_life)
    return round(max(0.01, min(1.0, intensity)), 2)


def _is_violent(category: str, description: str) -> bool:
    """Check whether an incident is classified as violent."""
    combined = f"{category} {description}".lower()
    return any(kw in combined for kw in VIOLENT_KEYWORDS)


def _compute_trend(current_count: int, prior_count: int) -> tuple[str, float]:
    """Compute trend label and percentage vs prior year."""
    if prior_count == 0:
        if current_count == 0:
            return "stable", 0.0
        return "increasing", 100.0
    pct = ((current_count - prior_count) / prior_count) * 100.0
    if pct > 5:
        return "increasing", round(pct, 1)
    if pct < -5:
        return "decreasing", round(pct, 1)
    return "stable", round(pct, 1)


def _cache_key(lat: float, lon: float, radius_miles: float, days_back: int) -> str:
    """Build a deterministic cache key for the crime query."""
    raw = f"crime:{lat:.6f}:{lon:.6f}:{radius_miles:.2f}:{days_back}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"crime:{digest}"


@router.get("/crime", response_model=CrimeResponse)
async def get_crime(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 1.0,
    days_back: Annotated[int, Query(ge=1, le=3650)] = 365,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> CrimeResponse:
    """Return crime data for the area around the given location."""
    # Check cache
    c_key = _cache_key(lat, lon, radius_miles, days_back)
    if valkey is not None:
        try:
            cached = await valkey.get(c_key)
            if cached is not None:
                data = json.loads(cached)
                return CrimeResponse(**data)
        except Exception:
            logger.warning("Valkey read failed for key %s", c_key, exc_info=True)

    now = datetime.now(tz=UTC)
    cutoff_date = (now - timedelta(days=days_back)).date()
    radius_meters = radius_miles * METERS_PER_MILE

    # Build the geography point for ST_DWithin
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query gold table directly
    base_query = select(
        PoliceIncident.incident_id,
        PoliceIncident.latitude.label("lat"),
        PoliceIncident.longitude.label("lon"),
        PoliceIncident.date_of_incident,
        func.coalesce(PoliceIncident.crime_description, "Unknown").label("description"),
        func.coalesce(PoliceIncident.crime_category, "Other").label("category"),
    ).where(
        PoliceIncident.location.isnot(None),
        PoliceIncident.date_of_incident >= cutoff_date,
        _st_dwithin_geography(PoliceIncident.location, property_point, radius_meters),
    )

    rows = db.execute(base_query.order_by(PoliceIncident.date_of_incident.desc())).all()

    # Build heatmap points (all incidents)
    heatmap: list[CrimeHeatmapPoint] = []
    for row in rows:
        if row.lat is not None and row.lon is not None and row.date_of_incident is not None:
            intensity = _compute_intensity(row.date_of_incident, now, days_back)
            heatmap.append(CrimeHeatmapPoint(lat=row.lat, lon=row.lon, intensity=intensity))

    # Build incident list (first 50, sorted by date desc)
    incidents: list[CrimeIncident] = []
    for row in rows[:50]:
        if row.lat is not None and row.lon is not None:
            incidents.append(
                CrimeIncident(
                    id=row.incident_id,
                    incident_type=row.description or "Unknown",
                    category=row.category or "Other",
                    date=(
                        row.date_of_incident.strftime("%Y-%m-%d")
                        if row.date_of_incident
                        else "Unknown"
                    ),
                    lat=row.lat,
                    lon=row.lon,
                    description=row.description,
                )
            )

    # Compute metrics
    total = len(rows)
    area_sq_km = math.pi * (radius_miles * 1.60934) ** 2
    incidents_per_sq_km = round(total / area_sq_km, 1) if area_sq_km > 0 else 0.0
    # Approximate per-1000 using density (no census pop data available)
    incidents_per_1000 = round(incidents_per_sq_km * 0.5, 1)

    # Trend: compare current period vs prior period of same length
    prior_cutoff = (now - timedelta(days=days_back * 2)).date()
    current_count = total
    prior_total_result = db.execute(
        select(func.count()).select_from(
            select(PoliceIncident.incident_id)
            .where(
                PoliceIncident.location.isnot(None),
                PoliceIncident.date_of_incident >= prior_cutoff,
                PoliceIncident.date_of_incident < cutoff_date,
                _st_dwithin_geography(PoliceIncident.location, property_point, radius_meters),
            )
            .subquery()
        )
    ).scalar()
    prior_count = prior_total_result or 0

    trend_label, _trend_pct = _compute_trend(current_count, prior_count)

    # crime_z_score: simple normalization around regional baseline
    baseline_density = 50.0
    z_score = (
        round(
            (incidents_per_sq_km - baseline_density) / max(baseline_density * 0.3, 1),
            2,
        )
        if total > 0
        else 0.0
    )

    metrics = CrimeMetrics(
        total_incidents_1mi=total,
        incidents_per_1000_people=incidents_per_1000,
        crime_z_score=z_score,
        trend=trend_label,
    )

    response = CrimeResponse(
        heatmap=heatmap,
        incidents=incidents,
        metrics=metrics,
    )

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
