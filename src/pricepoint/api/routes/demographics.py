"""Demographics endpoint — returns ACS census data for geographic contexts.

Choropleth map data and boundary geometry are now served via Martin vector
tiles (see docker/martin/config.yaml).  This module only provides the
statistical / chart data for the sidebar.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import (
    ST_Contains,
    ST_DWithin,
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
    BlockGroup,
    County,
    PropertyGeoLookup,
    RedfinListing,
    Subdivision,
    Township,
    Tract,
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


@router.get("/demographics", response_model=DemographicsResponse)
async def get_demographics(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    db: Annotated[Session, Depends(get_db)],
) -> DemographicsResponse:
    """Return ACS census demographics for geographic contexts around a point."""
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # 1. Try precomputed geo lookups first (fast path via B-tree indexes)
    geoid_map: dict[str, str] = {}  # geography_level → geoid

    lookup = db.execute(
        select(PropertyGeoLookup)
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .where(
            RedfinListing.location.isnot(None),
            ST_DWithin(RedfinListing.location, point, 0.001),
        )
        .limit(1)
    ).scalar_one_or_none()

    if lookup:
        if lookup.census_tract_geoid:
            geoid_map["tract"] = str(lookup.census_tract_geoid)
        if lookup.county_subdivision_geoid:
            geoid_map["county_subdivision"] = str(lookup.county_subdivision_geoid)
        if lookup.census_block_group_geoid:
            geoid_map["block_group"] = str(lookup.census_block_group_geoid)
        if lookup.county_geoid:
            geoid_map["county"] = str(lookup.county_geoid)
        if lookup.subdivision_id:
            geoid_map["subdivision"] = f"subdiv_{lookup.subdivision_id}"
    else:
        # Fallback: spatial containment queries for unlisted addresses
        tract = db.execute(
            select(Tract.geoid).where(ST_Contains(Tract.geom, point)).limit(1)
        ).scalar_one_or_none()
        if tract:
            geoid_map["tract"] = str(tract)

        cousub = db.execute(
            select(Township.geoid).where(ST_Contains(Township.geom, point)).limit(1)
        ).scalar_one_or_none()
        if cousub:
            geoid_map["county_subdivision"] = str(cousub)

        block_group = db.execute(
            select(BlockGroup.geoid).where(ST_Contains(BlockGroup.geom, point)).limit(1)
        ).scalar_one_or_none()
        if block_group:
            geoid_map["block_group"] = str(block_group)

        county = db.execute(
            select(County.geoid).where(ST_Contains(County.geom, point)).limit(1)
        ).scalar_one_or_none()
        if county:
            geoid_map["county"] = str(county)

        subdiv = db.execute(
            select(Subdivision.id).where(ST_Contains(Subdivision.geom, point)).limit(1)
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

    return DemographicsResponse(
        contexts=contexts,
        benchmarks=benchmarks,
    )
