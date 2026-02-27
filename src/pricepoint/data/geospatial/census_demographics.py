"""Collect ACS 5-Year demographic estimates from the Census Bureau API.

Downloads population, age, race, income, education, home ownership, and
home value data at multiple geographic levels for multiple non-overlapping
vintages (e.g. 2009, 2014, 2019, 2024) and loads them into PostGIS.

Data is fetched for all 50 US states plus DC, iterating per state for
sub-national geographies (tract, block group, county subdivision).

Supported geography levels:
  - us, state, county, county_subdivision (from Census API)
  - tract, block_group (from Census API)
  - subdivision (area-weighted aggregation from block group data)
"""

import logging

import httpx
from sqlalchemy import delete, func, select, text

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import AcsDemographic

logger = logging.getLogger(__name__)

# Census API allows max 50 variables per request.
# We split into 3 chunks: demographics+age, income+education, housing.

# B01001: Sex by Age (total, male sub-vars, female sub-vars)
# Male age vars: B01001_003E..B01001_025E (23 vars)
# Female age vars: B01001_027E..B01001_049E (23 vars)
_B01001_MALE_VARS = [f"B01001_{i:03d}E" for i in range(3, 26)]
_B01001_FEMALE_VARS = [f"B01001_{i:03d}E" for i in range(27, 50)]

_CHUNK_1_VARS = (
    # B01001 totals + sub-vars
    ["B01001_001E", "B01001_002E", "B01001_026E"]
    + _B01001_MALE_VARS
    + _B01001_FEMALE_VARS
    # B01002 median age
    + ["B01002_001E"]
)  # 50

# Chunk 2: Race (8) + Hispanic (3) + Income brackets (17) + Median income (1) = 29
_CHUNK_2_VARS = (
    [f"B02001_{i:03d}E" for i in range(1, 9)]
    + [f"B03003_{i:03d}E" for i in range(1, 4)]
    + [f"B19001_{i:03d}E" for i in range(1, 18)]
    + ["B19013_001E"]
)  # 29

# Chunk 3: Education (25) + Tenure (3) + Median home value (1) = 29
# B15003 (Educational Attainment) is available from 2014+.
# For older vintages (e.g. 2009), we fall back to B15002 (Sex by Educational Attainment).
_CHUNK_3_VARS_B15003 = (
    [f"B15003_{i:03d}E" for i in range(1, 26)]
    + [f"B25003_{i:03d}E" for i in range(1, 4)]
    + ["B25077_001E"]
)  # 29

# B15002: Sex by Educational Attainment (35 vars) + Tenure (3) + Median home value (1) = 39
_CHUNK_3_VARS_B15002 = (
    [f"B15002_{i:03d}E" for i in range(1, 36)]
    + [f"B25003_{i:03d}E" for i in range(1, 4)]
    + ["B25077_001E"]
)  # 39

# Year threshold: B15003 available from 2014 ACS 5-year onward
_B15003_MIN_YEAR = 2014

# Male age bracket index ranges (1-based within B01001 male sub-vars 003-025)
# Under 5: 003, 5-9: 004, 10-14: 005, 15-17: 006
# 18-19: 007, 20: 008, 21: 009, 22-24: 010, 25-29: 011, 30-34: 012
# 35-39: 013, 40-44: 014, 45-49: 015, 50-54: 016
# 55-59: 017, 60-61: 018, 62-64: 019
# 65-66: 020, 67-69: 021, 70-74: 022, 75-79: 023, 80-84: 024, 85+: 025
_MALE_UNDER_18 = [f"B01001_{i:03d}E" for i in range(3, 7)]  # 003-006
_MALE_18_TO_22 = [f"B01001_{i:03d}E" for i in range(7, 10)]  # 007-009 (18-19, 20, 21)
_MALE_23_TO_29 = [f"B01001_{i:03d}E" for i in range(10, 12)]  # 010-011 (22-24, 25-29)
_MALE_30_TO_39 = [f"B01001_{i:03d}E" for i in range(12, 14)]  # 012-013 (30-34, 35-39)
_MALE_40_TO_49 = [f"B01001_{i:03d}E" for i in range(14, 16)]  # 014-015 (40-44, 45-49)
_MALE_50_TO_64 = [f"B01001_{i:03d}E" for i in range(16, 20)]  # 016-019 (50-54..62-64)
_MALE_65_PLUS = [f"B01001_{i:03d}E" for i in range(20, 26)]  # 020-025

# Female counterparts (offset by 24: female vars start at 027)
_FEMALE_UNDER_18 = [f"B01001_{i:03d}E" for i in range(27, 31)]
_FEMALE_18_TO_22 = [f"B01001_{i:03d}E" for i in range(31, 34)]  # 031-033
_FEMALE_23_TO_29 = [f"B01001_{i:03d}E" for i in range(34, 36)]  # 034-035
_FEMALE_30_TO_39 = [f"B01001_{i:03d}E" for i in range(36, 38)]  # 036-037
_FEMALE_40_TO_49 = [f"B01001_{i:03d}E" for i in range(38, 40)]  # 038-039
_FEMALE_50_TO_64 = [f"B01001_{i:03d}E" for i in range(40, 44)]  # 040-043
_FEMALE_65_PLUS = [f"B01001_{i:03d}E" for i in range(44, 50)]

_SENTINEL = "-666666666"

# All 50 US states + DC FIPS codes (used for per-state iteration)
_US_STATE_FIPS = [
    "01",
    "02",
    "04",
    "05",
    "06",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "53",
    "54",
    "55",
    "56",
]

# Geography parameter configurations for Census API.
# Sub-national levels use state:{state_fips} in the "in" clause,
# iterated per state for nationwide collection.
_GEO_CONFIGS: dict[str, dict[str, str | list[str]]] = {
    "us": {
        "geo_for": "us:*",
        "geo_in": "",
        "geo_cols": ["us"],
    },
    "state": {
        "geo_for": "state:*",
        "geo_in": "",
        "geo_cols": ["state"],
    },
    "county": {
        "geo_for": "county:*",
        "geo_in": "state:{state_fips}",
        "geo_cols": ["state", "county"],
    },
    "county subdivision": {
        "geo_for": "county subdivision:*",
        "geo_in": "state:{state_fips}",
        "geo_cols": ["state", "county", "county subdivision"],
    },
    "tract": {
        "geo_for": "tract:*",
        "geo_in": "state:{state_fips}",
        "geo_cols": ["state", "county", "tract"],
    },
    "block group": {
        "geo_for": "block group:*",
        "geo_in": "state:{state_fips} county:*",
        "geo_cols": ["state", "county", "tract", "block group"],
    },
}

# Count fields that should be summed with area weights in subdivision aggregation
_COUNT_FIELDS = [
    "total_population",
    "male_population",
    "female_population",
    "pop_under_18",
    "pop_18_to_22",
    "pop_23_to_29",
    "pop_30_to_39",
    "pop_40_to_49",
    "pop_50_to_64",
    "pop_65_plus",
    "race_white",
    "race_black",
    "race_american_indian",
    "race_asian",
    "race_pacific_islander",
    "race_other",
    "race_two_or_more",
    "hispanic_total",
    "not_hispanic",
    "hispanic",
    "total_households",
    "hh_income_under_10k",
    "hh_income_10k_to_15k",
    "hh_income_15k_to_20k",
    "hh_income_20k_to_25k",
    "hh_income_25k_to_30k",
    "hh_income_30k_to_35k",
    "hh_income_35k_to_40k",
    "hh_income_40k_to_45k",
    "hh_income_45k_to_50k",
    "hh_income_50k_to_60k",
    "hh_income_60k_to_75k",
    "hh_income_75k_to_100k",
    "hh_income_100k_to_125k",
    "hh_income_125k_to_150k",
    "hh_income_150k_to_200k",
    "hh_income_200k_plus",
    "edu_total",
    "edu_less_than_hs",
    "edu_high_school",
    "edu_some_college",
    "edu_bachelors",
    "edu_graduate_plus",
    "housing_total_occupied",
    "housing_owner_occupied",
    "housing_renter_occupied",
]

# Median fields that use population-weighted averaging in subdivision aggregation
_MEDIAN_FIELDS = [
    "median_age",
    "median_household_income",
    "median_home_value",
]


def _safe_int(value: str | None) -> int | None:
    """Convert a Census API string value to int, handling None and sentinel."""
    if value is None or value == "" or str(value) == _SENTINEL:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: str | None) -> float | None:
    """Convert a Census API string value to float, handling None and sentinel."""
    if value is None or value == "" or str(value) == _SENTINEL:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_geoid(row: dict[str, str], geo_level: str) -> str:
    """Build GEOID from Census API response geography columns."""
    state = row.get("state", "")
    county = row.get("county", "")
    tract = row.get("tract", "")
    if geo_level == "us":
        return row.get("us", "1")
    if geo_level == "state":
        return state
    if geo_level == "county":
        return f"{state}{county}"
    if geo_level == "county subdivision":
        cousub = row.get("county subdivision", "")
        return f"{state}{county}{cousub}"
    if geo_level == "block group":
        block_group = row.get("block group", "")
        return f"{state}{county}{tract}{block_group}"
    # Default: tract
    return f"{state}{county}{tract}"


def _aggregate_age_brackets(row: dict[str, str]) -> dict[str, int | None]:
    """Aggregate B01001 sub-variables into 7 age buckets."""

    def _sum_vars(var_list: list[str]) -> int | None:
        vals = [_safe_int(row.get(v)) for v in var_list]
        non_none = [v for v in vals if v is not None]
        return sum(non_none) if non_none else None

    return {
        "pop_under_18": _sum_vars(_MALE_UNDER_18 + _FEMALE_UNDER_18),
        "pop_18_to_22": _sum_vars(_MALE_18_TO_22 + _FEMALE_18_TO_22),
        "pop_23_to_29": _sum_vars(_MALE_23_TO_29 + _FEMALE_23_TO_29),
        "pop_30_to_39": _sum_vars(_MALE_30_TO_39 + _FEMALE_30_TO_39),
        "pop_40_to_49": _sum_vars(_MALE_40_TO_49 + _FEMALE_40_TO_49),
        "pop_50_to_64": _sum_vars(_MALE_50_TO_64 + _FEMALE_50_TO_64),
        "pop_65_plus": _sum_vars(_MALE_65_PLUS + _FEMALE_65_PLUS),
    }


def _aggregate_education(row: dict[str, str], year: int) -> dict[str, int | None]:
    """Aggregate education sub-variables into 5 education buckets.

    Uses B15003 for 2014+ vintages, falls back to B15002 for older vintages.
    B15002 splits by sex, so we sum male + female for each level.
    """

    def _sum_vars(var_list: list[str]) -> int | None:
        vals = [_safe_int(row.get(v)) for v in var_list]
        non_none = [v for v in vals if v is not None]
        return sum(non_none) if non_none else None

    if year >= _B15003_MIN_YEAR:
        return {
            "edu_total": _safe_int(row.get("B15003_001E")),
            # No schooling through 12th grade no diploma (002-016)
            "edu_less_than_hs": _sum_vars([f"B15003_{i:03d}E" for i in range(2, 17)]),
            # High school diploma + GED (017-018)
            "edu_high_school": _sum_vars([f"B15003_{i:03d}E" for i in range(17, 19)]),
            # Some college + associate's (019-021)
            "edu_some_college": _sum_vars([f"B15003_{i:03d}E" for i in range(19, 22)]),
            # Bachelor's (022)
            "edu_bachelors": _safe_int(row.get("B15003_022E")),
            # Master's + professional + doctorate (023-025)
            "edu_graduate_plus": _sum_vars([f"B15003_{i:03d}E" for i in range(23, 26)]),
        }

    # B15002 fallback: Male (003-018) + Female (020-035)
    return {
        "edu_total": _safe_int(row.get("B15002_001E")),
        # Less than HS: Male no schooling-12th no diploma (003-010) +
        #               Female no schooling-12th no diploma (020-027)
        "edu_less_than_hs": _sum_vars(
            [f"B15002_{i:03d}E" for i in range(3, 11)] + [f"B15002_{i:03d}E" for i in range(20, 28)]
        ),
        # High school: Male HS grad (011) + Female HS grad (028)
        "edu_high_school": _sum_vars(["B15002_011E", "B15002_028E"]),
        # Some college + associate's: Male (012-014) + Female (029-031)
        "edu_some_college": _sum_vars(
            [f"B15002_{i:03d}E" for i in range(12, 15)]
            + [f"B15002_{i:03d}E" for i in range(29, 32)]
        ),
        # Bachelor's: Male (015) + Female (032)
        "edu_bachelors": _sum_vars(["B15002_015E", "B15002_032E"]),
        # Graduate+: Male master's+professional+doctorate (016-018) +
        #            Female master's+professional+doctorate (033-035)
        "edu_graduate_plus": _sum_vars(
            [f"B15002_{i:03d}E" for i in range(16, 19)]
            + [f"B15002_{i:03d}E" for i in range(33, 36)]
        ),
    }


def _map_demographic_kwargs(row: dict[str, str], acs_year: int) -> dict:
    """Extract shared demographic column values from a Census API row."""
    age = _aggregate_age_brackets(row)
    edu = _aggregate_education(row, acs_year)
    return {
        "name": row.get("NAME"),
        "acs_year": acs_year,
        "total_population": _safe_int(row.get("B01001_001E")),
        "male_population": _safe_int(row.get("B01001_002E")),
        "female_population": _safe_int(row.get("B01001_026E")),
        "pop_under_18": age["pop_under_18"],
        "pop_18_to_22": age["pop_18_to_22"],
        "pop_23_to_29": age["pop_23_to_29"],
        "pop_30_to_39": age["pop_30_to_39"],
        "pop_40_to_49": age["pop_40_to_49"],
        "pop_50_to_64": age["pop_50_to_64"],
        "pop_65_plus": age["pop_65_plus"],
        "median_age": _safe_float(row.get("B01002_001E")),
        "race_white": _safe_int(row.get("B02001_002E")),
        "race_black": _safe_int(row.get("B02001_003E")),
        "race_american_indian": _safe_int(row.get("B02001_004E")),
        "race_asian": _safe_int(row.get("B02001_005E")),
        "race_pacific_islander": _safe_int(row.get("B02001_006E")),
        "race_other": _safe_int(row.get("B02001_007E")),
        "race_two_or_more": _safe_int(row.get("B02001_008E")),
        "hispanic_total": _safe_int(row.get("B03003_001E")),
        "not_hispanic": _safe_int(row.get("B03003_002E")),
        "hispanic": _safe_int(row.get("B03003_003E")),
        "total_households": _safe_int(row.get("B19001_001E")),
        "hh_income_under_10k": _safe_int(row.get("B19001_002E")),
        "hh_income_10k_to_15k": _safe_int(row.get("B19001_003E")),
        "hh_income_15k_to_20k": _safe_int(row.get("B19001_004E")),
        "hh_income_20k_to_25k": _safe_int(row.get("B19001_005E")),
        "hh_income_25k_to_30k": _safe_int(row.get("B19001_006E")),
        "hh_income_30k_to_35k": _safe_int(row.get("B19001_007E")),
        "hh_income_35k_to_40k": _safe_int(row.get("B19001_008E")),
        "hh_income_40k_to_45k": _safe_int(row.get("B19001_009E")),
        "hh_income_45k_to_50k": _safe_int(row.get("B19001_010E")),
        "hh_income_50k_to_60k": _safe_int(row.get("B19001_011E")),
        "hh_income_60k_to_75k": _safe_int(row.get("B19001_012E")),
        "hh_income_75k_to_100k": _safe_int(row.get("B19001_013E")),
        "hh_income_100k_to_125k": _safe_int(row.get("B19001_014E")),
        "hh_income_125k_to_150k": _safe_int(row.get("B19001_015E")),
        "hh_income_150k_to_200k": _safe_int(row.get("B19001_016E")),
        "hh_income_200k_plus": _safe_int(row.get("B19001_017E")),
        "median_household_income": _safe_int(row.get("B19013_001E")),
        "edu_total": edu["edu_total"],
        "edu_less_than_hs": edu["edu_less_than_hs"],
        "edu_high_school": edu["edu_high_school"],
        "edu_some_college": edu["edu_some_college"],
        "edu_bachelors": edu["edu_bachelors"],
        "edu_graduate_plus": edu["edu_graduate_plus"],
        "housing_total_occupied": _safe_int(row.get("B25003_001E")),
        "housing_owner_occupied": _safe_int(row.get("B25003_002E")),
        "housing_renter_occupied": _safe_int(row.get("B25003_003E")),
        "median_home_value": _safe_int(row.get("B25077_001E")),
    }


def _map_record(
    row: dict[str, str], acs_year: int, geo_level: str, geography_level: str
) -> AcsDemographic:
    """Map a merged Census API row to an AcsDemographic model."""
    kwargs = _map_demographic_kwargs(row, acs_year)
    return AcsDemographic(
        geography_level=geography_level,
        geoid=_extract_geoid(row, geo_level),
        **kwargs,
    )


def _fetch_acs_data(
    year: int,
    variables: list[str],
    geo_level: str,
    state_fips: str = "",
    county_fips: str = "",
) -> list[dict[str, str]]:
    """Fetch ACS data, chunking if >50 variables, and merge rows by GEOID.

    Returns a list of dicts with all variable values keyed by variable name,
    plus geography columns (state, county, tract, block group, NAME).
    """
    settings = get_settings()
    if not settings.census_api_key:
        raise RuntimeError("CENSUS_API_KEY is not set")

    base_url = f"{settings.census_acs_base_url}/{year}/acs/acs5"

    # Geography parameter from config
    config = _GEO_CONFIGS[geo_level]
    geo_for = str(config["geo_for"]).format(state_fips=state_fips, county_fips=county_fips)
    geo_in_raw = str(config["geo_in"]).format(state_fips=state_fips, county_fips=county_fips)
    geo_cols: list[str] = list(config["geo_cols"])  # type: ignore[arg-type]

    # Split into chunks of 49 (leave room for NAME)
    chunk_size = 49
    chunks = [variables[i : i + chunk_size] for i in range(0, len(variables), chunk_size)]

    merged: dict[str, dict[str, str]] = {}

    for chunk in chunks:
        get_param = ",".join(["NAME"] + chunk)
        params: dict[str, str] = {
            "get": get_param,
            "for": geo_for,
            "key": settings.census_api_key,
        }
        if geo_in_raw:
            params["in"] = geo_in_raw
        response = httpx.get(base_url, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) < 2:
            continue

        headers = data[0]
        for row_values in data[1:]:
            row_dict = dict(zip(headers, row_values, strict=False))
            geoid = _extract_geoid(row_dict, geo_level)
            if geoid not in merged:
                merged[geoid] = {}
                for col in geo_cols:
                    merged[geoid][col] = row_dict.get(col, "")
                merged[geoid]["NAME"] = row_dict.get("NAME", "")
            # Merge variable values
            for var in chunk:
                if var in row_dict:
                    merged[geoid][var] = row_dict[var]

    return list(merged.values())


def _get_all_vars(year: int) -> list[str]:
    """Return the full variable list for a given ACS vintage year."""
    chunk_3 = _CHUNK_3_VARS_B15003 if year >= _B15003_MIN_YEAR else _CHUNK_3_VARS_B15002
    return _CHUNK_1_VARS + _CHUNK_2_VARS + chunk_3


def _level_exists(session, year: int, geography_level: str) -> bool:  # type: ignore[no-untyped-def]
    """Return True if records already exist for this level+year."""
    count = session.execute(
        select(func.count())
        .select_from(AcsDemographic)
        .where(
            AcsDemographic.geography_level == geography_level,
            AcsDemographic.acs_year == year,
        )
    ).scalar()
    return bool(count and count > 0)


def _upsert_level(
    session,  # type: ignore[no-untyped-def]
    year: int,
    geography_level: str,
    records: list[AcsDemographic],
) -> None:
    """Delete existing records for a level+year, then insert new ones."""
    session.execute(
        delete(AcsDemographic).where(
            AcsDemographic.geography_level == geography_level,
            AcsDemographic.acs_year == year,
        )
    )
    session.commit()
    # Batch inserts for large record sets
    batch_size = 5000
    for i in range(0, len(records), batch_size):
        session.add_all(records[i : i + batch_size])
        session.commit()


def _fetch_nationwide(
    year: int,
    geo_level: str,
    geography_level: str,
) -> list[AcsDemographic]:
    """Fetch ACS data for all US states at the given geography level.

    Iterates over all 51 state FIPS codes (50 states + DC), fetching
    data per state and combining results.
    """
    all_vars = _get_all_vars(year)
    records: list[AcsDemographic] = []
    for state_fips in _US_STATE_FIPS:
        rows = _fetch_acs_data(year, all_vars, geo_level, state_fips=state_fips)
        for r in rows:
            records.append(_map_record(r, year, geo_level, geography_level))
        logger.info("  State %s: %d %s records", state_fips, len(rows), geography_level)
    return records


def fetch_acs_tract_demographics() -> None:
    """Fetch ACS tract demographics for all configured vintages (nationwide)."""
    settings = get_settings()

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            if _level_exists(session, year, "tract"):
                logger.info("Skipping ACS tract vintage %d — already loaded", year)
                continue
            logger.info("Fetching ACS tract demographics for vintage %d (all states)", year)
            records = _fetch_nationwide(year, "tract", "tract")
            _upsert_level(session, year, "tract", records)
            logger.info("Loaded %d tract records for vintage %d", len(records), year)

        logger.info("ACS tract demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_acs_block_group_demographics() -> None:
    """Fetch ACS block group demographics for eligible vintages (nationwide).

    Block group geography is not available in the Census API for early ACS
    5-year releases (e.g. 2009).  The ``census_acs_block_group_min_year``
    setting controls which vintages are included.
    """
    settings = get_settings()
    min_year = settings.census_acs_block_group_min_year
    vintages = [y for y in settings.census_acs_vintages if y >= min_year]
    if not vintages:
        logger.warning(
            "No ACS vintages eligible for block group fetch (min_year=%d)",
            settings.census_acs_block_group_min_year,
        )
        return

    session = SessionLocal()
    try:
        for year in vintages:
            if _level_exists(session, year, "block_group"):
                logger.info("Skipping ACS block group vintage %d — already loaded", year)
                continue
            logger.info("Fetching ACS block group demographics for vintage %d (all states)", year)
            records = _fetch_nationwide(year, "block group", "block_group")
            _upsert_level(session, year, "block_group", records)
            logger.info("Loaded %d block group records for vintage %d", len(records), year)

        logger.info("ACS block group demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_acs_summary_demographics() -> None:
    """Fetch ACS demographics for national, state, and county levels (nationwide).

    US and state levels are fetched in a single API call each.
    County level iterates per state.
    """
    settings = get_settings()

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            all_vars = _get_all_vars(year)

            # US level — single request
            if not _level_exists(session, year, "us"):
                logger.info("Fetching ACS us demographics for vintage %d", year)
                rows = _fetch_acs_data(year, all_vars, "us")
                records = [_map_record(r, year, "us", "us") for r in rows]
                _upsert_level(session, year, "us", records)
                logger.info("Loaded %d us records for vintage %d", len(records), year)
            else:
                logger.info("Skipping ACS us vintage %d — already loaded", year)

            # State level — single request returns all states
            if not _level_exists(session, year, "state"):
                logger.info("Fetching ACS state demographics for vintage %d", year)
                rows = _fetch_acs_data(year, all_vars, "state")
                records = [_map_record(r, year, "state", "state") for r in rows]
                _upsert_level(session, year, "state", records)
                logger.info("Loaded %d state records for vintage %d", len(records), year)
            else:
                logger.info("Skipping ACS state vintage %d — already loaded", year)

            # County level — iterate per state
            if not _level_exists(session, year, "county"):
                logger.info("Fetching ACS county demographics for vintage %d (all states)", year)
                records = _fetch_nationwide(year, "county", "county")
                _upsert_level(session, year, "county", records)
                logger.info("Loaded %d county records for vintage %d", len(records), year)
            else:
                logger.info("Skipping ACS county vintage %d — already loaded", year)

        logger.info("ACS summary demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_acs_county_sub_demographics() -> None:
    """Fetch ACS county subdivision demographics for all configured vintages (nationwide)."""
    settings = get_settings()

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            if _level_exists(session, year, "county_subdivision"):
                logger.info("Skipping ACS county subdivision vintage %d — already loaded", year)
                continue
            logger.info(
                "Fetching ACS county subdivision demographics for vintage %d (all states)", year
            )
            records = _fetch_nationwide(year, "county subdivision", "county_subdivision")
            _upsert_level(session, year, "county_subdivision", records)
            logger.info("Loaded %d county subdivision records for vintage %d", len(records), year)

        logger.info("ACS county subdivision demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def compute_subdivision_demographics() -> None:
    """Compute Wake subdivision demographics via area-weighted aggregation from block groups.

    For each Wake subdivision, overlaps with TIGER block groups are computed using
    ST_Intersects. Count fields are summed with area-proportion weights. Median fields
    use population-weighted averages (documented approximation).

    The geoid pattern is ``<county_geoid>S<subdivision_objectid>``,
    e.g. ``37183S329933``.
    """
    settings = get_settings()
    county_geoid = f"{settings.tiger_state_fips}{settings.tiger_county_fips}"

    # Build SQL column expressions for count and median fields
    count_cols = ",\n".join(
        f"        ROUND(SUM(o.weight * ad.{f}))::int AS {f}" for f in _COUNT_FIELDS
    )
    median_cols = ",\n".join(
        f"        CASE WHEN SUM(o.weight * ad.total_population) > 0\n"
        f"             THEN SUM(o.weight * ad.total_population * ad.{f})\n"
        f"                  / SUM(o.weight * ad.total_population)\n"
        f"             ELSE NULL END AS {f}"
        for f in _MEDIAN_FIELDS
    )

    sql = text(f"""
        WITH bg_overlaps AS (
            SELECT
                ws.objectid AS subdivision_objectid,
                ws.name AS subdivision_name,
                ad.geoid AS bg_geoid,
                ST_Area(ST_Intersection(ST_MakeValid(ws.geom), ST_MakeValid(tbg.geom))::geography)
                    / NULLIF(ST_Area(tbg.geom::geography), 0) AS weight
            FROM wake_subdivisions ws
            JOIN block_groups tbg
                ON ST_Intersects(ST_MakeValid(ws.geom), ST_MakeValid(tbg.geom))
            JOIN acs_demographics ad
                ON tbg.geoid = ad.geoid
                AND ad.geography_level = 'block_group'
                AND ad.acs_year = :year
        )
        SELECT
            o.subdivision_objectid,
            o.subdivision_name,
    {count_cols},
    {median_cols}
        FROM bg_overlaps o
        JOIN acs_demographics ad
            ON o.bg_geoid = ad.geoid
            AND ad.geography_level = 'block_group'
            AND ad.acs_year = :year
        GROUP BY o.subdivision_objectid, o.subdivision_name
        HAVING SUM(o.weight * ad.total_population) > 0
    """)

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            if _level_exists(session, year, "subdivision"):
                logger.info("Skipping subdivision vintage %d — already loaded", year)
                continue
            logger.info("Computing subdivision demographics for vintage %d", year)
            result = session.execute(sql, {"year": year})
            rows = result.fetchall()
            columns = list(result.keys())
            logger.info("Computed %d subdivision aggregations for vintage %d", len(rows), year)

            records = []
            for row in rows:
                row_dict = dict(zip(columns, row, strict=False))
                objectid = row_dict["subdivision_objectid"]
                geoid = f"{county_geoid}S{objectid}"
                kwargs: dict = {
                    "geography_level": "subdivision",
                    "geoid": geoid,
                    "name": row_dict["subdivision_name"],
                    "acs_year": year,
                }
                for f in _COUNT_FIELDS:
                    val = row_dict.get(f)
                    kwargs[f] = int(val) if val is not None else None
                for f in _MEDIAN_FIELDS:
                    val = row_dict.get(f)
                    if val is not None:
                        if f == "median_age":
                            kwargs[f] = round(float(val), 2)
                        else:
                            kwargs[f] = int(round(float(val)))
                    else:
                        kwargs[f] = None
                records.append(AcsDemographic(**kwargs))

            _upsert_level(session, year, "subdivision", records)
            logger.info("Loaded %d subdivision records for vintage %d", len(records), year)

        logger.info("Subdivision demographics computation complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_acs_demographics() -> None:
    """Verify that ACS demographic records were loaded for all levels and vintages."""
    settings = get_settings()
    session = SessionLocal()

    expected_levels = [
        "us",
        "state",
        "county",
        "county_subdivision",
        "tract",
        "block_group",
        "subdivision",
    ]

    try:
        total = session.execute(select(func.count()).select_from(AcsDemographic)).scalar()
        if not total:
            raise RuntimeError("No records found in acs_demographics after load")
        logger.info("Verified %d total records in acs_demographics", total)

        for level in expected_levels:
            level_total = session.execute(
                select(func.count())
                .select_from(AcsDemographic)
                .where(AcsDemographic.geography_level == level)
            ).scalar()
            logger.info("  Level %s: %d total records", level, level_total)
            for year in settings.census_acs_vintages:
                count = session.execute(
                    select(func.count())
                    .select_from(AcsDemographic)
                    .where(
                        AcsDemographic.geography_level == level,
                        AcsDemographic.acs_year == year,
                    )
                ).scalar()
                logger.info("    Vintage %d: %d records", year, count)
    finally:
        session.close()
