"""Collect ACS 5-Year demographic estimates from the Census Bureau API.

Downloads population, age, race, income, education, home ownership, and
home value data at tract and block group levels for multiple non-overlapping
vintages (e.g. 2009, 2014, 2019, 2024) and loads them into PostGIS.
"""

import logging

import httpx
from sqlalchemy import delete, func, select

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import AcsBlockGroupDemographic, AcsTractDemographic

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
    # B02001 race (8 vars)
    + [f"B02001_{i:03d}E" for i in range(1, 9)]
    # B03003 hispanic (3 vars)
    + [f"B03003_{i:03d}E" for i in range(1, 4)]
)  # 3+23+23+1+8+3 = 61 → split needed

# Actually let's re-chunk to stay under 50 per request.
# Chunk 1: B01001 totals + male age + female age + B01002 median age = 3+23+23+1 = 50
_CHUNK_1_VARS = (
    ["B01001_001E", "B01001_002E", "B01001_026E"]
    + _B01001_MALE_VARS
    + _B01001_FEMALE_VARS
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
_MALE_18_TO_34 = [f"B01001_{i:03d}E" for i in range(7, 13)]  # 007-012
_MALE_35_TO_54 = [f"B01001_{i:03d}E" for i in range(13, 17)]  # 013-016
_MALE_55_TO_64 = [f"B01001_{i:03d}E" for i in range(17, 20)]  # 017-019
_MALE_65_PLUS = [f"B01001_{i:03d}E" for i in range(20, 26)]  # 020-025

# Female counterparts (offset by 24: female vars start at 027)
_FEMALE_UNDER_18 = [f"B01001_{i:03d}E" for i in range(27, 31)]
_FEMALE_18_TO_34 = [f"B01001_{i:03d}E" for i in range(31, 37)]
_FEMALE_35_TO_54 = [f"B01001_{i:03d}E" for i in range(37, 41)]
_FEMALE_55_TO_64 = [f"B01001_{i:03d}E" for i in range(41, 44)]
_FEMALE_65_PLUS = [f"B01001_{i:03d}E" for i in range(44, 50)]

_SENTINEL = "-666666666"


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
    if geo_level == "block group":
        block_group = row.get("block group", "")
        return f"{state}{county}{tract}{block_group}"
    return f"{state}{county}{tract}"


def _aggregate_age_brackets(row: dict[str, str]) -> dict[str, int | None]:
    """Aggregate B01001 sub-variables into 5 age buckets."""

    def _sum_vars(var_list: list[str]) -> int | None:
        vals = [_safe_int(row.get(v)) for v in var_list]
        non_none = [v for v in vals if v is not None]
        return sum(non_none) if non_none else None

    return {
        "pop_under_18": _sum_vars(_MALE_UNDER_18 + _FEMALE_UNDER_18),
        "pop_18_to_34": _sum_vars(_MALE_18_TO_34 + _FEMALE_18_TO_34),
        "pop_35_to_54": _sum_vars(_MALE_35_TO_54 + _FEMALE_35_TO_54),
        "pop_55_to_64": _sum_vars(_MALE_55_TO_64 + _FEMALE_55_TO_64),
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


def _map_tract_record(row: dict[str, str], acs_year: int) -> AcsTractDemographic:
    """Map a merged Census API row to an AcsTractDemographic model."""
    age = _aggregate_age_brackets(row)
    edu = _aggregate_education(row, acs_year)
    return AcsTractDemographic(
        geoid=_extract_geoid(row, "tract"),
        name=row.get("NAME"),
        acs_year=acs_year,
        total_population=_safe_int(row.get("B01001_001E")),
        male_population=_safe_int(row.get("B01001_002E")),
        female_population=_safe_int(row.get("B01001_026E")),
        pop_under_18=age["pop_under_18"],
        pop_18_to_34=age["pop_18_to_34"],
        pop_35_to_54=age["pop_35_to_54"],
        pop_55_to_64=age["pop_55_to_64"],
        pop_65_plus=age["pop_65_plus"],
        median_age=_safe_float(row.get("B01002_001E")),
        race_white=_safe_int(row.get("B02001_002E")),
        race_black=_safe_int(row.get("B02001_003E")),
        race_american_indian=_safe_int(row.get("B02001_004E")),
        race_asian=_safe_int(row.get("B02001_005E")),
        race_pacific_islander=_safe_int(row.get("B02001_006E")),
        race_other=_safe_int(row.get("B02001_007E")),
        race_two_or_more=_safe_int(row.get("B02001_008E")),
        hispanic_total=_safe_int(row.get("B03003_001E")),
        not_hispanic=_safe_int(row.get("B03003_002E")),
        hispanic=_safe_int(row.get("B03003_003E")),
        total_households=_safe_int(row.get("B19001_001E")),
        hh_income_under_10k=_safe_int(row.get("B19001_002E")),
        hh_income_10k_to_15k=_safe_int(row.get("B19001_003E")),
        hh_income_15k_to_20k=_safe_int(row.get("B19001_004E")),
        hh_income_20k_to_25k=_safe_int(row.get("B19001_005E")),
        hh_income_25k_to_30k=_safe_int(row.get("B19001_006E")),
        hh_income_30k_to_35k=_safe_int(row.get("B19001_007E")),
        hh_income_35k_to_40k=_safe_int(row.get("B19001_008E")),
        hh_income_40k_to_45k=_safe_int(row.get("B19001_009E")),
        hh_income_45k_to_50k=_safe_int(row.get("B19001_010E")),
        hh_income_50k_to_60k=_safe_int(row.get("B19001_011E")),
        hh_income_60k_to_75k=_safe_int(row.get("B19001_012E")),
        hh_income_75k_to_100k=_safe_int(row.get("B19001_013E")),
        hh_income_100k_to_125k=_safe_int(row.get("B19001_014E")),
        hh_income_125k_to_150k=_safe_int(row.get("B19001_015E")),
        hh_income_150k_to_200k=_safe_int(row.get("B19001_016E")),
        hh_income_200k_plus=_safe_int(row.get("B19001_017E")),
        median_household_income=_safe_int(row.get("B19013_001E")),
        edu_total=edu["edu_total"],
        edu_less_than_hs=edu["edu_less_than_hs"],
        edu_high_school=edu["edu_high_school"],
        edu_some_college=edu["edu_some_college"],
        edu_bachelors=edu["edu_bachelors"],
        edu_graduate_plus=edu["edu_graduate_plus"],
        housing_total_occupied=_safe_int(row.get("B25003_001E")),
        housing_owner_occupied=_safe_int(row.get("B25003_002E")),
        housing_renter_occupied=_safe_int(row.get("B25003_003E")),
        median_home_value=_safe_int(row.get("B25077_001E")),
    )


def _map_block_group_record(row: dict[str, str], acs_year: int) -> AcsBlockGroupDemographic:
    """Map a merged Census API row to an AcsBlockGroupDemographic model."""
    age = _aggregate_age_brackets(row)
    edu = _aggregate_education(row, acs_year)
    return AcsBlockGroupDemographic(
        geoid=_extract_geoid(row, "block group"),
        name=row.get("NAME"),
        acs_year=acs_year,
        total_population=_safe_int(row.get("B01001_001E")),
        male_population=_safe_int(row.get("B01001_002E")),
        female_population=_safe_int(row.get("B01001_026E")),
        pop_under_18=age["pop_under_18"],
        pop_18_to_34=age["pop_18_to_34"],
        pop_35_to_54=age["pop_35_to_54"],
        pop_55_to_64=age["pop_55_to_64"],
        pop_65_plus=age["pop_65_plus"],
        median_age=_safe_float(row.get("B01002_001E")),
        race_white=_safe_int(row.get("B02001_002E")),
        race_black=_safe_int(row.get("B02001_003E")),
        race_american_indian=_safe_int(row.get("B02001_004E")),
        race_asian=_safe_int(row.get("B02001_005E")),
        race_pacific_islander=_safe_int(row.get("B02001_006E")),
        race_other=_safe_int(row.get("B02001_007E")),
        race_two_or_more=_safe_int(row.get("B02001_008E")),
        hispanic_total=_safe_int(row.get("B03003_001E")),
        not_hispanic=_safe_int(row.get("B03003_002E")),
        hispanic=_safe_int(row.get("B03003_003E")),
        total_households=_safe_int(row.get("B19001_001E")),
        hh_income_under_10k=_safe_int(row.get("B19001_002E")),
        hh_income_10k_to_15k=_safe_int(row.get("B19001_003E")),
        hh_income_15k_to_20k=_safe_int(row.get("B19001_004E")),
        hh_income_20k_to_25k=_safe_int(row.get("B19001_005E")),
        hh_income_25k_to_30k=_safe_int(row.get("B19001_006E")),
        hh_income_30k_to_35k=_safe_int(row.get("B19001_007E")),
        hh_income_35k_to_40k=_safe_int(row.get("B19001_008E")),
        hh_income_40k_to_45k=_safe_int(row.get("B19001_009E")),
        hh_income_45k_to_50k=_safe_int(row.get("B19001_010E")),
        hh_income_50k_to_60k=_safe_int(row.get("B19001_011E")),
        hh_income_60k_to_75k=_safe_int(row.get("B19001_012E")),
        hh_income_75k_to_100k=_safe_int(row.get("B19001_013E")),
        hh_income_100k_to_125k=_safe_int(row.get("B19001_014E")),
        hh_income_125k_to_150k=_safe_int(row.get("B19001_015E")),
        hh_income_150k_to_200k=_safe_int(row.get("B19001_016E")),
        hh_income_200k_plus=_safe_int(row.get("B19001_017E")),
        median_household_income=_safe_int(row.get("B19013_001E")),
        edu_total=edu["edu_total"],
        edu_less_than_hs=edu["edu_less_than_hs"],
        edu_high_school=edu["edu_high_school"],
        edu_some_college=edu["edu_some_college"],
        edu_bachelors=edu["edu_bachelors"],
        edu_graduate_plus=edu["edu_graduate_plus"],
        housing_total_occupied=_safe_int(row.get("B25003_001E")),
        housing_owner_occupied=_safe_int(row.get("B25003_002E")),
        housing_renter_occupied=_safe_int(row.get("B25003_003E")),
        median_home_value=_safe_int(row.get("B25077_001E")),
    )


def _fetch_acs_data(
    year: int,
    variables: list[str],
    geo_level: str,
    state_fips: str,
    county_fips: str,
) -> list[dict[str, str]]:
    """Fetch ACS data, chunking if >50 variables, and merge rows by GEOID.

    Returns a list of dicts with all variable values keyed by variable name,
    plus geography columns (state, county, tract, block group, NAME).
    """
    settings = get_settings()
    if not settings.census_api_key:
        raise RuntimeError("CENSUS_API_KEY is not set")

    base_url = f"{settings.census_acs_base_url}/{year}/acs/acs5"

    # Geography parameter
    if geo_level == "block group":
        geo_for = "block group:*"
        geo_in = f"state:{state_fips}+county:{county_fips}+tract:*"
        geo_cols = ["state", "county", "tract", "block group"]
    else:
        geo_for = "tract:*"
        geo_in = f"state:{state_fips}+county:{county_fips}"
        geo_cols = ["state", "county", "tract"]

    # Split into chunks of 49 (leave room for NAME)
    chunk_size = 49
    chunks = [variables[i : i + chunk_size] for i in range(0, len(variables), chunk_size)]

    merged: dict[str, dict[str, str]] = {}

    for chunk in chunks:
        get_param = ",".join(["NAME"] + chunk)
        params = {
            "get": get_param,
            "for": geo_for,
            "in": geo_in,
            "key": settings.census_api_key,
        }
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


def fetch_acs_tract_demographics() -> None:
    """Fetch ACS tract demographics for all configured vintages."""
    settings = get_settings()

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            logger.info("Fetching ACS tract demographics for vintage %d", year)
            all_vars = _get_all_vars(year)
            rows = _fetch_acs_data(
                year, all_vars, "tract", settings.tiger_state_fips, settings.tiger_county_fips
            )
            logger.info("Received %d tract records for vintage %d", len(rows), year)

            # Delete existing rows for this vintage, then insert
            session.execute(delete(AcsTractDemographic).where(AcsTractDemographic.acs_year == year))
            session.commit()

            records = [_map_tract_record(r, year) for r in rows]
            session.add_all(records)
            session.commit()
            logger.info("Loaded %d tract records for vintage %d", len(records), year)

        logger.info("ACS tract demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fetch_acs_block_group_demographics() -> None:
    """Fetch ACS block group demographics for all configured vintages."""
    settings = get_settings()

    session = SessionLocal()
    try:
        for year in settings.census_acs_vintages:
            logger.info("Fetching ACS block group demographics for vintage %d", year)
            all_vars = _get_all_vars(year)
            rows = _fetch_acs_data(
                year,
                all_vars,
                "block group",
                settings.tiger_state_fips,
                settings.tiger_county_fips,
            )
            logger.info("Received %d block group records for vintage %d", len(rows), year)

            session.execute(
                delete(AcsBlockGroupDemographic).where(AcsBlockGroupDemographic.acs_year == year)
            )
            session.commit()

            records = [_map_block_group_record(r, year) for r in rows]
            session.add_all(records)
            session.commit()
            logger.info("Loaded %d block group records for vintage %d", len(records), year)

        logger.info("ACS block group demographics load complete")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_acs_demographics() -> None:
    """Verify that ACS demographic records were loaded for all vintages."""
    settings = get_settings()
    session = SessionLocal()
    try:
        # Tract demographics
        total = session.execute(select(func.count()).select_from(AcsTractDemographic)).scalar()
        if not total:
            raise RuntimeError("No records found in acs_tract_demographics after load")
        logger.info("Verified %d total records in acs_tract_demographics", total)
        for year in settings.census_acs_vintages:
            count = session.execute(
                select(func.count())
                .select_from(AcsTractDemographic)
                .where(AcsTractDemographic.acs_year == year)
            ).scalar()
            logger.info("  Vintage %d: %d records in acs_tract_demographics", year, count)

        # Block group demographics
        total = session.execute(select(func.count()).select_from(AcsBlockGroupDemographic)).scalar()
        if not total:
            raise RuntimeError("No records found in acs_block_group_demographics after load")
        logger.info("Verified %d total records in acs_block_group_demographics", total)
        for year in settings.census_acs_vintages:
            count = session.execute(
                select(func.count())
                .select_from(AcsBlockGroupDemographic)
                .where(AcsBlockGroupDemographic.acs_year == year)
            ).scalar()
            logger.info("  Vintage %d: %d records in acs_block_group_demographics", year, count)
    finally:
        session.close()
