"""Demographics endpoint — returns ACS census data for geographic contexts."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_Contains,
    ST_Expand,
    ST_Intersects,
    ST_MakeEnvelope,
    ST_MakePoint,
    ST_SetSRID,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.demographics import (
    AgeBucket,
    AgeDistributionTrendPoint,
    DemographicContextData,
    DemographicsResponse,
    HomeOwnershipTrendPoint,
    IncomeTrendPoint,
    LabelValue,
    MedianAgeTrendPoint,
    PopulationTrendPoint,
    RaceEthnicityTrendPoint,
)
from pricepoint.db.models import (
    AcsDemographic,
    TigerBlockGroup,
    TigerCounty,
    TigerCountySubdivision,
    TigerTract,
    WakeSubdivision,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demographics"])

# ── Geography level → frontend context key mapping ──
_LEVEL_TO_CONTEXT: dict[str, str] = {
    "tract": "neighborhood",
    "county_subdivision": "town",
    "subdivision": "subdivision",
    "block_group": "block_group",
    "county": "county",
}

_BENCHMARK_LEVELS = ("us", "state")

# Choropleth config per context key
_ChoroCfg = tuple[Any, str, float, str, str | None, str]
# (model_cls, acs_level, default_buffer, geoid_attr, name_attr, geoid_prefix)
_CHOROPLETH_CONFIG: dict[str, _ChoroCfg] = {}


def _init_choropleth_config() -> None:
    """Lazily populate config after model imports are available."""
    if _CHOROPLETH_CONFIG:
        return
    _CHOROPLETH_CONFIG.update(
        {
            "neighborhood": (TigerTract, "tract", 0.05, "geoid", None, ""),
            "block_group": (TigerBlockGroup, "block_group", 0.03, "geoid", None, ""),
            "town": (
                TigerCountySubdivision,
                "county_subdivision",
                0.15,
                "geoid",
                "name",
                "",
            ),
            "county": (TigerCounty, "county", 0.5, "geoid", "name", ""),
            "subdivision": (WakeSubdivision, "subdivision", 0.03, "id", "name", "subdiv_"),
        }
    )


# ── Pure transformation helpers ──


def consolidate_race(row: Any) -> list[LabelValue]:
    """Consolidate ACS race + Hispanic data into 5 display categories.

    Hispanic overlaps with race categories.  We approximate non-Hispanic white
    by scaling ``race_white`` by the ``not_hispanic / total`` ratio.  The
    remaining categories are taken as-is and the whole set is normalised to 100%.
    """
    total = row.total_population or 0
    if total == 0:
        return [
            LabelValue(label=lbl, value=0)
            for lbl in ("White", "Black", "Hispanic", "Asian", "Other")
        ]

    hispanic = row.hispanic or 0
    not_hispanic = row.not_hispanic or 0
    nh_ratio = not_hispanic / total if total else 0

    white = (row.race_white or 0) * nh_ratio
    black = row.race_black or 0
    asian = row.race_asian or 0
    other = (
        (row.race_american_indian or 0)
        + (row.race_pacific_islander or 0)
        + (row.race_other or 0)
        + (row.race_two_or_more or 0)
    )

    raw = {"White": white, "Black": black, "Hispanic": hispanic, "Asian": asian, "Other": other}
    raw_total = sum(raw.values())
    if raw_total == 0:
        return [LabelValue(label=lbl, value=0) for lbl in raw]

    return [
        LabelValue(label=lbl, value=round(val / raw_total * 100, 1)) for lbl, val in raw.items()
    ]


def consolidate_income(row: Any) -> list[LabelValue]:
    """Consolidate 16 ACS income brackets into 6 display brackets (percentages)."""
    total = row.total_households or 0
    if total == 0:
        return [
            LabelValue(label=lbl, value=0)
            for lbl in ("<$25k", "$25-50k", "$50-100k", "$100-150k", "$150-200k", "$200k+")
        ]

    under_25k = sum(
        getattr(row, attr, 0) or 0
        for attr in (
            "hh_income_under_10k",
            "hh_income_10k_to_15k",
            "hh_income_15k_to_20k",
            "hh_income_20k_to_25k",
        )
    )
    b25_50 = sum(
        getattr(row, attr, 0) or 0
        for attr in (
            "hh_income_25k_to_30k",
            "hh_income_30k_to_35k",
            "hh_income_35k_to_40k",
            "hh_income_40k_to_45k",
            "hh_income_45k_to_50k",
        )
    )
    b50_100 = sum(
        getattr(row, attr, 0) or 0
        for attr in (
            "hh_income_50k_to_60k",
            "hh_income_60k_to_75k",
            "hh_income_75k_to_100k",
        )
    )
    b100_150 = sum(
        getattr(row, attr, 0) or 0 for attr in ("hh_income_100k_to_125k", "hh_income_125k_to_150k")
    )
    b150_200 = getattr(row, "hh_income_150k_to_200k", 0) or 0
    b200_plus = getattr(row, "hh_income_200k_plus", 0) or 0

    brackets = [
        ("<$25k", under_25k),
        ("$25-50k", b25_50),
        ("$50-100k", b50_100),
        ("$100-150k", b100_150),
        ("$150-200k", b150_200),
        ("$200k+", b200_plus),
    ]
    return [LabelValue(label=lbl, value=round(val / total * 100, 1)) for lbl, val in brackets]


def estimate_age_split(row: Any) -> list[AgeBucket]:
    """Split 7 age buckets into male/female percentages using population ratio."""
    total = row.total_population or 0
    if total == 0:
        labels = ["<18", "18-22", "23-29", "30-39", "40-49", "50-64", "65+"]
        return [AgeBucket(range=lbl, male=0, female=0) for lbl in labels]

    male_ratio = (row.male_population or 0) / total if total else 0.5
    female_ratio = 1.0 - male_ratio

    buckets = [
        ("<18", row.pop_under_18 or 0),
        ("18-22", row.pop_18_to_22 or 0),
        ("23-29", row.pop_23_to_29 or 0),
        ("30-39", row.pop_30_to_39 or 0),
        ("40-49", row.pop_40_to_49 or 0),
        ("50-64", row.pop_50_to_64 or 0),
        ("65+", row.pop_65_plus or 0),
    ]

    return [
        AgeBucket(
            range=label,
            male=round((count / total * 100) * male_ratio, 1),
            female=round((count / total * 100) * female_ratio, 1),
        )
        for label, count in buckets
    ]


def build_context_data(rows: list[Any]) -> DemographicContextData | None:
    """Build a DemographicContextData from ACS rows (multiple vintages).

    Uses the most recent year for the snapshot and all years for trends.
    Returns None if no rows are provided.
    """
    if not rows:
        return None

    sorted_rows = sorted(rows, key=lambda r: r.acs_year)
    latest = sorted_rows[-1]

    # Snapshot
    race = consolidate_race(latest)
    age = estimate_age_split(latest)
    income = consolidate_income(latest)

    total_occ = latest.housing_total_occupied or 0
    owner_occ = latest.housing_owner_occupied or 0
    ownership_rate = round(owner_occ / total_occ * 100, 1) if total_occ > 0 else 0.0

    # Trends
    pop_trend = [
        PopulationTrendPoint(year=r.acs_year, population=r.total_population or 0)
        for r in sorted_rows
    ]

    race_trend: list[RaceEthnicityTrendPoint] = []
    for r in sorted_rows:
        race_vals = consolidate_race(r)
        race_map = {rv.label: rv.value for rv in race_vals}
        race_trend.append(
            RaceEthnicityTrendPoint(
                year=r.acs_year,
                white=race_map.get("White", 0),
                black=race_map.get("Black", 0),
                hispanic=race_map.get("Hispanic", 0),
                asian=race_map.get("Asian", 0),
                other=race_map.get("Other", 0),
            )
        )

    age_trend: list[AgeDistributionTrendPoint] = []
    for r in sorted_rows:
        total = r.total_population or 0
        if total == 0:
            age_trend.append(
                AgeDistributionTrendPoint(
                    year=r.acs_year,
                    under18=0,
                    age18_22=0,
                    age23_29=0,
                    age30_39=0,
                    age40_49=0,
                    age50_64=0,
                    age65plus=0,
                )
            )
        else:
            age_trend.append(
                AgeDistributionTrendPoint(
                    year=r.acs_year,
                    under18=round((r.pop_under_18 or 0) / total * 100, 1),
                    age18_22=round((r.pop_18_to_22 or 0) / total * 100, 1),
                    age23_29=round((r.pop_23_to_29 or 0) / total * 100, 1),
                    age30_39=round((r.pop_30_to_39 or 0) / total * 100, 1),
                    age40_49=round((r.pop_40_to_49 or 0) / total * 100, 1),
                    age50_64=round((r.pop_50_to_64 or 0) / total * 100, 1),
                    age65plus=round((r.pop_65_plus or 0) / total * 100, 1),
                )
            )

    income_trend = [
        IncomeTrendPoint(year=r.acs_year, median_income=r.median_household_income or 0)
        for r in sorted_rows
    ]

    ownership_trend: list[HomeOwnershipTrendPoint] = []
    for r in sorted_rows:
        t_occ = r.housing_total_occupied or 0
        o_occ = r.housing_owner_occupied or 0
        rate = round(o_occ / t_occ * 100, 1) if t_occ > 0 else 0.0
        ownership_trend.append(HomeOwnershipTrendPoint(year=r.acs_year, ownership_rate=rate))

    median_age_trend = [
        MedianAgeTrendPoint(year=r.acs_year, median_age=r.median_age or 0) for r in sorted_rows
    ]

    return DemographicContextData(
        race_ethnicity=race,
        age_distribution=age,
        median_income=latest.median_household_income or 0,
        income_brackets=income,
        home_ownership_rate=ownership_rate,
        median_home_value=latest.median_home_value or 0,
        population=latest.total_population or 0,
        population_trend=pop_trend,
        race_ethnicity_trend=race_trend,
        age_distribution_trend=age_trend,
        income_trend=income_trend,
        home_ownership_trend=ownership_trend,
        median_age_trend=median_age_trend,
    )


def _empty_context() -> DemographicContextData:
    """Return an empty context with zero values for all fields."""
    labels = ["White", "Black", "Hispanic", "Asian", "Other"]
    age_labels = ["<18", "18-22", "23-29", "30-39", "40-49", "50-64", "65+"]
    income_labels = ["<$25k", "$25-50k", "$50-100k", "$100-150k", "$150-200k", "$200k+"]
    return DemographicContextData(
        race_ethnicity=[LabelValue(label=lb, value=0) for lb in labels],
        age_distribution=[AgeBucket(range=lb, male=0, female=0) for lb in age_labels],
        median_income=0,
        income_brackets=[LabelValue(label=lb, value=0) for lb in income_labels],
        home_ownership_rate=0,
        median_home_value=0,
        population=0,
        population_trend=[],
        race_ethnicity_trend=[],
        age_distribution_trend=[],
        income_trend=[],
        home_ownership_trend=[],
        median_age_trend=[],
    )


def _compute_feature_props(
    row: Any | None,
    geoid: str,
    name: str,
    is_home: bool,
) -> dict[str, Any]:
    """Extract choropleth feature properties from an ACS row."""
    if row is None:
        return {
            "geoid": geoid,
            "name": name,
            "is_home": is_home,
            "population": 0,
            "median_income": 0,
            "median_age": 0,
            "home_ownership_rate": 0,
            "dominant_race": "Unknown",
            "dominant_race_pct": 0,
            "pct_under_18": 0,
            "pct_65_plus": 0,
            "pct_white": 0,
            "pct_black": 0,
            "pct_hispanic": 0,
            "pct_asian": 0,
            "pct_other": 0,
        }

    total_pop = row.total_population or 0
    total_occ = row.housing_total_occupied or 0
    owner_occ = row.housing_owner_occupied or 0
    ownership_rate = round(owner_occ / total_occ * 100, 1) if total_occ > 0 else 0

    # Dominant race + per-race percentages
    race_vals = consolidate_race(row)
    dominant = max(race_vals, key=lambda r: r.value) if race_vals else None
    race_map = {rv.label.lower(): rv.value for rv in race_vals}

    pct_under_18 = round((row.pop_under_18 or 0) / total_pop * 100, 1) if total_pop > 0 else 0
    pct_65_plus = round((row.pop_65_plus or 0) / total_pop * 100, 1) if total_pop > 0 else 0

    return {
        "geoid": geoid,
        "name": name,
        "is_home": is_home,
        "population": total_pop,
        "median_income": row.median_household_income or 0,
        "median_age": row.median_age or 0,
        "home_ownership_rate": ownership_rate,
        "dominant_race": dominant.label if dominant else "Unknown",
        "dominant_race_pct": dominant.value if dominant else 0,
        "pct_under_18": pct_under_18,
        "pct_65_plus": pct_65_plus,
        "pct_white": race_map.get("white", 0),
        "pct_black": race_map.get("black", 0),
        "pct_hispanic": race_map.get("hispanic", 0),
        "pct_asian": race_map.get("asian", 0),
        "pct_other": race_map.get("other", 0),
    }


def _build_choropleth_level(
    db: Session,
    model_cls: Any,
    acs_level: str,
    envelope: Any,
    home_geoid: str | None,
    *,
    geoid_attr: str = "geoid",
    name_attr: str | None = None,
    geoid_prefix: str = "",
) -> list[dict[str, Any]]:
    """Build GeoJSON Feature list for a single choropleth level.

    ``envelope`` should be a PostGIS geometry (e.g. from ``ST_MakeEnvelope``)
    that defines the area of interest.
    """
    geoid_col = getattr(model_cls, geoid_attr)
    geom_col = model_cls.geom

    # Optionally fetch a name column alongside geoid
    columns = [geoid_col, ST_AsGeoJSON(geom_col).label("geojson")]
    has_name = False
    if name_attr and hasattr(model_cls, name_attr):
        columns.append(getattr(model_cls, name_attr))
        has_name = True

    # Query geometries intersecting the envelope
    nearby = db.execute(select(*columns).where(ST_Intersects(geom_col, envelope))).all()

    if not nearby:
        return []

    # Collect all geoids for batch ACS fetch
    raw_geoids = [str(row[0]) for row in nearby]
    acs_geoids = [f"{geoid_prefix}{g}" for g in raw_geoids]

    # Batch-fetch most recent ACS data (DISTINCT ON geoid)
    acs_map: dict[str, Any] = {}
    if acs_geoids:
        acs_stmt = (
            select(AcsDemographic)
            .where(
                AcsDemographic.geography_level == acs_level,
                AcsDemographic.geoid.in_(acs_geoids),
            )
            .order_by(AcsDemographic.geoid, AcsDemographic.acs_year.desc())
            .distinct(AcsDemographic.geoid)
        )
        for ar in db.execute(acs_stmt).scalars().all():
            acs_map[str(ar.geoid)] = ar

    features: list[dict[str, Any]] = []
    for row_tuple in nearby:
        raw_geoid_str = str(row_tuple[0])
        geojson_str = row_tuple[1]
        display_name = str(row_tuple[2]) if has_name else raw_geoid_str
        acs_geoid = f"{geoid_prefix}{raw_geoid_str}"
        acs_row: Any = acs_map.get(acs_geoid)

        is_home = acs_geoid == home_geoid if home_geoid else False

        props = _compute_feature_props(acs_row, acs_geoid, display_name, is_home)
        geojson_dict = json.loads(geojson_str)
        features.append(
            {
                "type": "Feature",
                "geometry": geojson_dict,
                "properties": props,
            }
        )

    return features


@router.get("/demographics", response_model=DemographicsResponse)
async def get_demographics(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
) -> DemographicsResponse:
    """Return ACS census demographics for geographic contexts around a point."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # 1. Spatial lookups to find geoids
    geoid_map: dict[str, str] = {}  # geography_level → geoid

    tract = db.execute(
        select(TigerTract.geoid).where(ST_Contains(TigerTract.geom, point)).limit(1)
    ).scalar_one_or_none()
    if tract:
        geoid_map["tract"] = str(tract)

    cousub = db.execute(
        select(TigerCountySubdivision.geoid)
        .where(ST_Contains(TigerCountySubdivision.geom, point))
        .limit(1)
    ).scalar_one_or_none()
    if cousub:
        geoid_map["county_subdivision"] = str(cousub)

    block_group = db.execute(
        select(TigerBlockGroup.geoid).where(ST_Contains(TigerBlockGroup.geom, point)).limit(1)
    ).scalar_one_or_none()
    if block_group:
        geoid_map["block_group"] = str(block_group)

    county = db.execute(
        select(TigerCounty.geoid).where(ST_Contains(TigerCounty.geom, point)).limit(1)
    ).scalar_one_or_none()
    if county:
        geoid_map["county"] = str(county)

    subdiv = db.execute(
        select(WakeSubdivision.snumber).where(ST_Contains(WakeSubdivision.geom, point)).limit(1)
    ).scalar_one_or_none()
    if subdiv:
        geoid_map["subdivision"] = f"subdiv_{subdiv}"

    # 2. Query ACS demographics for matched geoids + benchmarks
    all_geoids = list(geoid_map.values())

    acs_rows: list[AcsDemographic] = []
    if all_geoids or _BENCHMARK_LEVELS:
        stmt = select(AcsDemographic).where(
            or_(
                AcsDemographic.geography_level.in_(list(geoid_map.keys()))
                & AcsDemographic.geoid.in_(all_geoids),
                AcsDemographic.geography_level.in_(list(_BENCHMARK_LEVELS)),
            )
        )
        acs_rows = list(db.execute(stmt).scalars().all())

    # Group rows by (geography_level, geoid) → list of vintage rows
    grouped: dict[tuple[str, str], list[Any]] = {}
    for row in acs_rows:
        key: tuple[str, str] = (str(row.geography_level), str(row.geoid))
        grouped.setdefault(key, []).append(row)

    # 3. Build context data
    contexts: dict[str, DemographicContextData] = {}
    for level, context_key in _LEVEL_TO_CONTEXT.items():
        geoid = geoid_map.get(level)
        if geoid:
            rows = grouped.get((level, geoid), [])
            ctx = build_context_data(rows)
            contexts[context_key] = ctx if ctx else _empty_context()
        else:
            contexts[context_key] = _empty_context()

    # 4. Build benchmarks (us, state)
    benchmarks: dict[str, DemographicContextData] = {}
    benchmark_names = {"us": "national", "state": "state"}
    for level, bm_key in benchmark_names.items():
        level_rows = [r for r in acs_rows if r.geography_level == level]
        if level_rows:
            # Group by geoid (should be one for us/state)
            by_geoid: dict[str, list[Any]] = {}
            for r in level_rows:
                by_geoid.setdefault(str(r.geoid), []).append(r)
            # Use first geoid
            first_geoid_rows = list(by_geoid.values())[0]
            bm = build_context_data(first_geoid_rows)
            benchmarks[bm_key] = bm if bm else _empty_context()
        else:
            benchmarks[bm_key] = _empty_context()

    # 5. Boundaries — return GeoJSON for matched geographies
    boundaries: dict[str, dict[str, Any] | None] = {}

    if tract:
        geojson_str = db.execute(
            select(ST_AsGeoJSON(TigerTract.geom)).where(TigerTract.geoid == tract).limit(1)
        ).scalar_one_or_none()
        boundaries["neighborhood"] = json.loads(geojson_str) if geojson_str else None
    else:
        boundaries["neighborhood"] = None

    if cousub:
        geojson_str = db.execute(
            select(ST_AsGeoJSON(TigerCountySubdivision.geom))
            .where(TigerCountySubdivision.geoid == cousub)
            .limit(1)
        ).scalar_one_or_none()
        boundaries["town"] = json.loads(geojson_str) if geojson_str else None
    else:
        boundaries["town"] = None

    if subdiv:
        snumber = str(subdiv)
        geojson_str = db.execute(
            select(ST_AsGeoJSON(WakeSubdivision.geom))
            .where(WakeSubdivision.snumber == snumber)
            .limit(1)
        ).scalar_one_or_none()
        boundaries["subdivision"] = json.loads(geojson_str) if geojson_str else None
    else:
        boundaries["subdivision"] = None

    if block_group:
        geojson_str = db.execute(
            select(ST_AsGeoJSON(TigerBlockGroup.geom))
            .where(TigerBlockGroup.geoid == block_group)
            .limit(1)
        ).scalar_one_or_none()
        boundaries["block_group"] = json.loads(geojson_str) if geojson_str else None
    else:
        boundaries["block_group"] = None

    if county:
        geojson_str = db.execute(
            select(ST_AsGeoJSON(TigerCounty.geom)).where(TigerCounty.geoid == county).limit(1)
        ).scalar_one_or_none()
        boundaries["county"] = json.loads(geojson_str) if geojson_str else None
    else:
        boundaries["county"] = None

    # 6. Choropleth — initial set per context using buffer around property
    _init_choropleth_config()
    choropleth: dict[str, list[dict[str, Any]]] = {}
    for ctx_key, (
        model_cls,
        acs_level,
        buf,
        geoid_attr,
        name_col,
        prefix,
    ) in _CHOROPLETH_CONFIG.items():
        # Determine home geoid for this level's geoid_attr
        if prefix:
            # Subdivision: look up the id of the subdivision containing the point
            home_raw = db.execute(
                select(getattr(model_cls, geoid_attr))
                .where(ST_Contains(model_cls.geom, point))
                .limit(1)
            ).scalar_one_or_none()
            home = f"{prefix}{home_raw}" if home_raw else None
        else:
            home = geoid_map.get(acs_level)
        envelope = ST_Expand(point, buf)
        choropleth[ctx_key] = _build_choropleth_level(
            db,
            model_cls,
            acs_level,
            envelope,
            home,
            geoid_attr=geoid_attr,
            name_attr=name_col,
            geoid_prefix=prefix,
        )

    return DemographicsResponse(
        contexts=contexts,
        benchmarks=benchmarks,
        boundaries=boundaries,
        choropleth=choropleth,
    )


@router.get("/demographics/choropleth")
async def get_demographics_choropleth(
    context: Annotated[str, Query()],
    sw_lat: Annotated[float, Query(ge=-90, le=90)],
    sw_lon: Annotated[float, Query(ge=-180, le=180)],
    ne_lat: Annotated[float, Query(ge=-90, le=90)],
    ne_lon: Annotated[float, Query(ge=-180, le=180)],
    home_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    home_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    *,
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Return choropleth GeoJSON features within a bounding box.

    Called by the frontend when the map viewport changes (pan/zoom).
    """
    _init_choropleth_config()

    if context not in _CHOROPLETH_CONFIG:
        return []

    model_cls, acs_level, _default_buf, geoid_attr, name_col, prefix = _CHOROPLETH_CONFIG[context]
    envelope = ST_MakeEnvelope(sw_lon, sw_lat, ne_lon, ne_lat, 4326)

    # Determine home geoid if property coords provided
    home_geoid: str | None = None
    if home_lat is not None and home_lon is not None:
        home_point = ST_SetSRID(ST_MakePoint(home_lon, home_lat), 4326)
        home_raw = db.execute(
            select(getattr(model_cls, geoid_attr))
            .where(ST_Contains(model_cls.geom, home_point))
            .limit(1)
        ).scalar_one_or_none()
        if home_raw:
            home_geoid = f"{prefix}{home_raw}"

    return _build_choropleth_level(
        db,
        model_cls,
        acs_level,
        envelope,
        home_geoid,
        geoid_attr=geoid_attr,
        name_attr=name_col,
        geoid_prefix=prefix,
    )
