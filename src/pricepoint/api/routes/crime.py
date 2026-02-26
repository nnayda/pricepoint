"""Crime endpoint — returns crime data from PostGIS spatial queries."""

import hashlib
import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y, ST_MakePoint, ST_SetSRID
from redis.asyncio import Redis
from sqlalchemy import (
    DateTime,
    String,
    cast,
    func,
    literal,
    select,
    union_all,
)
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.crime import (
    CrimeHeatmapPoint,
    CrimeIncident,
    CrimeMetrics,
    CrimeResponse,
)
from pricepoint.db.models import (
    StagingCaryPoliceIncident,
    StagingMorrisvillePoliceIncident,
    StagingRaleighPoliceIncident,
)

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


def _build_crime_cte(
    property_point,  # noqa: ANN001
    radius_meters: float,
    cutoff_date: datetime,
):
    """Build a CTE unioning all three police staging tables with normalized columns."""
    # Cary: date_from (DateTime), crime_type (description), crime_category
    cary_q = select(
        cast(StagingCaryPoliceIncident.id, String).label("incident_id"),
        StagingCaryPoliceIncident.location.label("location"),
        cast(StagingCaryPoliceIncident.date_from, DateTime(timezone=True)).label("occurred_at"),
        func.coalesce(StagingCaryPoliceIncident.crime_type, "Unknown").label("description"),
        func.coalesce(StagingCaryPoliceIncident.crime_category, "Other").label("category"),
        literal("Cary").label("source_city"),
    ).where(
        StagingCaryPoliceIncident.location.isnot(None),
        StagingCaryPoliceIncident.date_from >= cutoff_date,
        _st_dwithin_geography(StagingCaryPoliceIncident.location, property_point, radius_meters),
    )

    # Raleigh: reported_date (DateTime), crime_description, crime_category
    raleigh_q = select(
        cast(StagingRaleighPoliceIncident.id, String).label("incident_id"),
        StagingRaleighPoliceIncident.location.label("location"),
        cast(StagingRaleighPoliceIncident.reported_date, DateTime(timezone=True)).label(
            "occurred_at"
        ),
        func.coalesce(StagingRaleighPoliceIncident.crime_description, "Unknown").label(
            "description"
        ),
        func.coalesce(StagingRaleighPoliceIncident.crime_category, "Other").label("category"),
        literal("Raleigh").label("source_city"),
    ).where(
        StagingRaleighPoliceIncident.location.isnot(None),
        StagingRaleighPoliceIncident.reported_date >= cutoff_date,
        _st_dwithin_geography(StagingRaleighPoliceIncident.location, property_point, radius_meters),
    )

    # Morrisville: date_occu (String!), offense (description), no dedicated category
    morrisville_q = select(
        cast(StagingMorrisvillePoliceIncident.id, String).label("incident_id"),
        StagingMorrisvillePoliceIncident.location.label("location"),
        cast(
            func.to_timestamp(StagingMorrisvillePoliceIncident.date_occu, "MM/DD/YYYY"),
            DateTime(timezone=True),
        ).label("occurred_at"),
        func.coalesce(StagingMorrisvillePoliceIncident.offense, "Unknown").label("description"),
        literal("Other").label("category"),
        literal("Morrisville").label("source_city"),
    ).where(
        StagingMorrisvillePoliceIncident.location.isnot(None),
        StagingMorrisvillePoliceIncident.date_occu.isnot(None),
        _st_dwithin_geography(
            StagingMorrisvillePoliceIncident.location,
            property_point,
            radius_meters,
        ),
    )

    combined = union_all(cary_q, raleigh_q, morrisville_q).cte("all_incidents")
    return combined


def _compute_intensity(occurred_at: datetime, now: datetime, days_back: int) -> float:
    """Compute heatmap intensity using exponential decay on recency.

    More recent incidents get higher intensity (closer to 1.0).
    Half-life is set to days_back / 4 so a quarter-period-old incident
    has intensity ~0.5.
    """
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
    cutoff_date = now - timedelta(days=days_back)
    radius_meters = radius_miles * METERS_PER_MILE

    # Build the geography point for ST_DWithin
    property_point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    cte = _build_crime_cte(property_point, radius_meters, cutoff_date)

    # Fetch all incidents in the area
    rows = db.execute(
        select(
            cte.c.incident_id,
            ST_Y(cte.c.location).label("lat"),
            ST_X(cte.c.location).label("lon"),
            cte.c.occurred_at,
            cte.c.description,
            cte.c.category,
            cte.c.source_city,
        ).order_by(cte.c.occurred_at.desc())
    ).all()

    # Build heatmap points (all incidents)
    heatmap: list[CrimeHeatmapPoint] = []
    for row in rows:
        if row.lat is not None and row.lon is not None and row.occurred_at is not None:
            intensity = _compute_intensity(row.occurred_at, now, days_back)
            heatmap.append(CrimeHeatmapPoint(lat=row.lat, lon=row.lon, intensity=intensity))

    # Build incident list (first 50, sorted by date desc)
    incidents: list[CrimeIncident] = []
    for row in rows[:50]:
        if row.lat is not None and row.lon is not None:
            incidents.append(
                CrimeIncident(
                    id=f"{row.source_city}-{row.incident_id}",
                    incident_type=row.description or "Unknown",
                    category=row.category or "Other",
                    date=(row.occurred_at.strftime("%Y-%m-%d") if row.occurred_at else "Unknown"),
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
    prior_cutoff = cutoff_date - timedelta(days=days_back)
    current_count = total
    prior_cte = _build_crime_cte(property_point, radius_meters, prior_cutoff)
    prior_total_result = db.execute(
        select(func.count()).select_from(
            select(prior_cte.c.incident_id).where(prior_cte.c.occurred_at < cutoff_date).subquery()
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
