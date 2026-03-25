"""initial_schema

Revision ID: 74d6d4a48980
Revises:
Create Date: 2026-03-12 03:56:48.555960

"""

from collections.abc import Sequence

import geoalchemy2  # noqa: F401
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Demographic view helpers
# ---------------------------------------------------------------------------
_DEMO_COLS = """
               d.total_population AS population,
               d.median_household_income AS median_income,
               d.median_age,
               CASE WHEN d.housing_total_occupied > 0
                    THEN round(d.housing_owner_occupied * 100.0
                               / d.housing_total_occupied, 1)::float8
               END AS home_ownership_rate,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_white * 100.0 / d.total_population, 1)::float8
               END AS pct_white,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_black * 100.0 / d.total_population, 1)::float8
               END AS pct_black,
               CASE WHEN d.total_population > 0
                    THEN round(d.hispanic * 100.0 / d.total_population, 1)::float8
               END AS pct_hispanic,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_asian * 100.0 / d.total_population, 1)::float8
               END AS pct_asian,
               CASE WHEN d.total_population > 0
                    THEN round(
                        (d.total_population
                         - COALESCE(d.race_white, 0)
                         - COALESCE(d.race_black, 0)
                         - COALESCE(d.hispanic, 0)
                         - COALESCE(d.race_asian, 0)
                        ) * 100.0 / d.total_population, 1)::float8
               END AS pct_other,
               CASE WHEN d.total_population > 0 THEN
                    (SELECT r.race FROM (VALUES
                        (d.race_white, 'White'),
                        (d.race_black, 'Black'),
                        (d.hispanic, 'Hispanic'),
                        (d.race_asian, 'Asian'),
                        (d.total_population
                         - COALESCE(d.race_white, 0)
                         - COALESCE(d.race_black, 0)
                         - COALESCE(d.hispanic, 0)
                         - COALESCE(d.race_asian, 0), 'Other')
                    ) AS r(cnt, race) ORDER BY r.cnt DESC NULLS LAST LIMIT 1)
               END AS dominant_race,
               CASE WHEN d.total_population > 0 THEN
                    round(
                        GREATEST(
                            COALESCE(d.race_white, 0),
                            COALESCE(d.race_black, 0),
                            COALESCE(d.hispanic, 0),
                            COALESCE(d.race_asian, 0),
                            d.total_population
                             - COALESCE(d.race_white, 0)
                             - COALESCE(d.race_black, 0)
                             - COALESCE(d.hispanic, 0)
                             - COALESCE(d.race_asian, 0)
                        ) * 100.0 / d.total_population, 1)::float8
               END AS dominant_race_pct"""

_ASIAN_SUB = """
               asian_sub.dominant_asian_subgroup,
               asian_sub.dominant_asian_subgroup_pct,
               asian_sub.pct_asian_indian,
               asian_sub.pct_chinese,
               asian_sub.pct_filipino,
               asian_sub.pct_japanese,
               asian_sub.pct_korean,
               asian_sub.pct_vietnamese,
               asian_sub.pct_other_asian"""


def _asian_lateral(geo_level: str, geoid_expr: str) -> str:
    """Return a LEFT JOIN LATERAL for dominant Asian subgroup computation."""
    return f"""
        LEFT JOIN LATERAL (
            SELECT
                (SELECT dr2.subgroup_label FROM acs_detailed_race dr2
                 WHERE dr2.geoid = {geoid_expr}
                   AND dr2.geography_level = '{geo_level}'
                   AND dr2.race_category = 'asian'
                   AND dr2.acs_year = (SELECT max(acs_year) FROM acs_detailed_race
                                       WHERE geography_level = '{geo_level}')
                 ORDER BY dr2.population DESC NULLS LAST LIMIT 1
                ) AS dominant_asian_subgroup,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(dr2.population * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr}
                      AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian'
                      AND dr2.acs_year = (SELECT max(acs_year) FROM acs_detailed_race
                                          WHERE geography_level = '{geo_level}')
                    ORDER BY dr2.population DESC NULLS LAST LIMIT 1
                ) END AS dominant_asian_subgroup_pct,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Asian Indian'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_asian_indian,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Chinese'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_chinese,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Filipino'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_filipino,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Japanese'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_japanese,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Korean'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_korean,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Vietnamese'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_vietnamese,
                CASE WHEN d.race_asian > 0 THEN (
                    SELECT round(COALESCE(sum(dr2.population), 0) * 100.0 / d.race_asian, 1)::float8
                    FROM acs_detailed_race dr2
                    WHERE dr2.geoid = {geoid_expr} AND dr2.geography_level = '{geo_level}'
                      AND dr2.race_category = 'asian' AND dr2.subgroup_label = 'Other Asian'
                      AND dr2.acs_year = (SELECT max(acs_year)
                          FROM acs_detailed_race
                          WHERE geography_level = '{geo_level}')
                ) END AS pct_other_asian
        ) asian_sub ON true"""


# revision identifiers, used by Alembic.
revision: str = "74d6d4a48980"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "acs_demographics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geography_level", sa.String(length=25), nullable=False),
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acs_year", sa.Integer(), nullable=False),
        sa.Column("total_population", sa.Integer(), nullable=True),
        sa.Column("male_population", sa.Integer(), nullable=True),
        sa.Column("female_population", sa.Integer(), nullable=True),
        sa.Column("pop_under_18", sa.Integer(), nullable=True),
        sa.Column("pop_18_to_22", sa.Integer(), nullable=True),
        sa.Column("pop_23_to_29", sa.Integer(), nullable=True),
        sa.Column("pop_30_to_39", sa.Integer(), nullable=True),
        sa.Column("pop_40_to_49", sa.Integer(), nullable=True),
        sa.Column("pop_50_to_64", sa.Integer(), nullable=True),
        sa.Column("pop_65_plus", sa.Integer(), nullable=True),
        sa.Column("median_age", sa.Float(), nullable=True),
        sa.Column("race_white", sa.Integer(), nullable=True),
        sa.Column("race_black", sa.Integer(), nullable=True),
        sa.Column("race_american_indian", sa.Integer(), nullable=True),
        sa.Column("race_asian", sa.Integer(), nullable=True),
        sa.Column("race_pacific_islander", sa.Integer(), nullable=True),
        sa.Column("race_other", sa.Integer(), nullable=True),
        sa.Column("race_two_or_more", sa.Integer(), nullable=True),
        sa.Column("hispanic_total", sa.Integer(), nullable=True),
        sa.Column("not_hispanic", sa.Integer(), nullable=True),
        sa.Column("hispanic", sa.Integer(), nullable=True),
        sa.Column("total_households", sa.Integer(), nullable=True),
        sa.Column("hh_income_under_10k", sa.Integer(), nullable=True),
        sa.Column("hh_income_10k_to_15k", sa.Integer(), nullable=True),
        sa.Column("hh_income_15k_to_20k", sa.Integer(), nullable=True),
        sa.Column("hh_income_20k_to_25k", sa.Integer(), nullable=True),
        sa.Column("hh_income_25k_to_30k", sa.Integer(), nullable=True),
        sa.Column("hh_income_30k_to_35k", sa.Integer(), nullable=True),
        sa.Column("hh_income_35k_to_40k", sa.Integer(), nullable=True),
        sa.Column("hh_income_40k_to_45k", sa.Integer(), nullable=True),
        sa.Column("hh_income_45k_to_50k", sa.Integer(), nullable=True),
        sa.Column("hh_income_50k_to_60k", sa.Integer(), nullable=True),
        sa.Column("hh_income_60k_to_75k", sa.Integer(), nullable=True),
        sa.Column("hh_income_75k_to_100k", sa.Integer(), nullable=True),
        sa.Column("hh_income_100k_to_125k", sa.Integer(), nullable=True),
        sa.Column("hh_income_125k_to_150k", sa.Integer(), nullable=True),
        sa.Column("hh_income_150k_to_200k", sa.Integer(), nullable=True),
        sa.Column("hh_income_200k_plus", sa.Integer(), nullable=True),
        sa.Column("median_household_income", sa.Integer(), nullable=True),
        sa.Column("edu_total", sa.Integer(), nullable=True),
        sa.Column("edu_less_than_hs", sa.Integer(), nullable=True),
        sa.Column("edu_high_school", sa.Integer(), nullable=True),
        sa.Column("edu_some_college", sa.Integer(), nullable=True),
        sa.Column("edu_bachelors", sa.Integer(), nullable=True),
        sa.Column("edu_graduate_plus", sa.Integer(), nullable=True),
        sa.Column("housing_total_occupied", sa.Integer(), nullable=True),
        sa.Column("housing_owner_occupied", sa.Integer(), nullable=True),
        sa.Column("housing_renter_occupied", sa.Integer(), nullable=True),
        sa.Column("median_home_value", sa.Integer(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "geography_level", "geoid", "acs_year", name="uq_acs_demo_level_geoid_year"
        ),
    )
    op.create_index(
        op.f("ix_acs_demographics_acs_year"), "acs_demographics", ["acs_year"], unique=False
    )
    op.create_index(
        op.f("ix_acs_demographics_geography_level"),
        "acs_demographics",
        ["geography_level"],
        unique=False,
    )
    op.create_index(op.f("ix_acs_demographics_geoid"), "acs_demographics", ["geoid"], unique=False)
    op.create_table(
        "acs_detailed_race",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geography_level", sa.String(length=25), nullable=False),
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("acs_year", sa.Integer(), nullable=False),
        sa.Column("race_category", sa.String(length=20), nullable=False),
        sa.Column("subgroup_code", sa.String(length=15), nullable=False),
        sa.Column("subgroup_label", sa.String(length=60), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "geography_level",
            "geoid",
            "acs_year",
            "subgroup_code",
            name="uq_acs_detail_race_geo_year_code",
        ),
    )
    op.create_index(
        "ix_acs_detail_race_category", "acs_detailed_race", ["race_category"], unique=False
    )
    op.create_index(
        "ix_acs_detail_race_lookup",
        "acs_detailed_race",
        ["geography_level", "geoid", "acs_year"],
        unique=False,
    )
    op.create_table(
        "airports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ident", sa.String(), nullable=False),
        sa.Column("airport_type", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("elevation_ft", sa.Integer(), nullable=True),
        sa.Column("iso_region", sa.String(), nullable=True),
        sa.Column("municipality", sa.String(), nullable=True),
        sa.Column("scheduled_service", sa.Boolean(), nullable=True),
        sa.Column("iata_code", sa.String(), nullable=True),
        sa.Column("home_link", sa.String(), nullable=True),
        sa.Column("wikipedia_link", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ident", name="uq_airports_ident"),
    )
    op.create_index("ix_airports_geom", "airports", ["geom"], unique=False, postgresql_using="gist")
    op.create_index(op.f("ix_airports_ident"), "airports", ["ident"], unique=False)
    op.create_index(op.f("ix_airports_name"), "airports", ["name"], unique=False)
    op.create_table(
        "block_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("tractce", sa.String(length=6), nullable=True),
        sa.Column("blkgrpce", sa.String(length=1), nullable=True),
        sa.Column("geoid", sa.String(length=12), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_block_groups_geoid"), "block_groups", ["geoid"], unique=False)
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp20", sa.String(length=2), nullable=True),
        sa.Column("countyfp20", sa.String(length=3), nullable=True),
        sa.Column("tractce20", sa.String(length=6), nullable=True),
        sa.Column("blockce20", sa.String(length=4), nullable=True),
        sa.Column("geoid20", sa.String(length=15), nullable=True),
        sa.Column("name20", sa.String(), nullable=True),
        sa.Column("aland20", sa.BigInteger(), nullable=True),
        sa.Column("awater20", sa.BigInteger(), nullable=True),
        sa.Column("intptlat20", sa.String(length=11), nullable=True),
        sa.Column("intptlon20", sa.String(length=12), nullable=True),
        sa.Column("funcstat20", sa.String(length=1), nullable=True),
        sa.Column("mtfcc20", sa.String(length=5), nullable=True),
        sa.Column("ur20", sa.String(length=1), nullable=True),
        sa.Column("uace20", sa.String(length=5), nullable=True),
        sa.Column("uatype20", sa.String(length=1), nullable=True),
        sa.Column("housing20", sa.Integer(), nullable=True),
        sa.Column("pop20", sa.Integer(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blocks_geoid20"), "blocks", ["geoid20"], unique=False)
    op.create_table(
        "cell_towers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("licensee", sa.String(), nullable=True),
        sa.Column("callsign", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("structure_type", sa.String(), nullable=True),
        sa.Column("height_ft", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cell_towers_geom", "cell_towers", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("ix_cell_towers_objectid"), "cell_towers", ["objectid"], unique=False)
    op.create_table(
        "counties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("countyns", sa.String(length=8), nullable=True),
        sa.Column("geoid", sa.String(length=5), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("classfp", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("csafp", sa.String(length=3), nullable=True),
        sa.Column("cbsafp", sa.String(length=5), nullable=True),
        sa.Column("metdivfp", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_counties_geoid"), "counties", ["geoid"], unique=False)
    op.create_table(
        "data_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("requested_by_email", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_requests_address"), "data_requests", ["address"], unique=False)
    op.create_table(
        "economic_indicators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.String(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "observation_date", name="uq_economic_series_date"),
    )
    op.create_index(
        "idx_economic_series_date",
        "economic_indicators",
        ["series_id", "observation_date"],
        unique=False,
    )
    op.create_table(
        "greenspace_region_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geo_level", sa.String(length=25), nullable=False),
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("park_count", sa.Integer(), nullable=False),
        sa.Column("trail_count", sa.Integer(), nullable=False),
        sa.Column("total_park_acres", sa.Float(), nullable=False),
        sa.Column("total_trail_miles", sa.Float(), nullable=False),
        sa.Column("greenspace_area_sqm", sa.Float(), nullable=False),
        sa.Column("region_land_area_sqm", sa.Float(), nullable=False),
        sa.Column("greenspace_ratio", sa.Float(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("parks_per_1k_residents", sa.Float(), nullable=True),
        sa.Column("greenspace_acres_per_1k_residents", sa.Float(), nullable=True),
        sa.Column("greenspace_ratio_zscore", sa.Float(), nullable=True),
        sa.Column("park_count_zscore", sa.Float(), nullable=True),
        sa.Column("trail_count_zscore", sa.Float(), nullable=True),
        sa.Column("total_park_acres_zscore", sa.Float(), nullable=True),
        sa.Column("total_trail_miles_zscore", sa.Float(), nullable=True),
        sa.Column("parks_per_1k_zscore", sa.Float(), nullable=True),
        sa.Column("greenspace_acres_per_1k_zscore", sa.Float(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("geo_level", "geoid", name="uq_greenspace_region_level_geoid"),
    )
    op.create_index(
        op.f("ix_greenspace_region_metrics_geo_level"),
        "greenspace_region_metrics",
        ["geo_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_greenspace_region_metrics_geoid"),
        "greenspace_region_metrics",
        ["geoid"],
        unique=False,
    )
    op.create_table(
        "greenspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("gis_acres", sa.Float(), nullable=True),
        sa.Column("manager_type", sa.String(length=10), nullable=True),
        sa.Column("manager_name", sa.String(), nullable=True),
        sa.Column("designation_type", sa.String(length=20), nullable=True),
        sa.Column("pub_access", sa.String(length=2), nullable=True),
        sa.Column("gap_sts", sa.Integer(), nullable=True),
        sa.Column("state_name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_greenspaces_geom", "greenspaces", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("ix_greenspaces_name"), "greenspaces", ["name"], unique=False)
    op.create_index(op.f("ix_greenspaces_source_id"), "greenspaces", ["source_id"], unique=True)
    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("hifld_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("telephone", sa.String(), nullable=True),
        sa.Column("hospital_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("countyfips", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("trauma", sa.String(), nullable=True),
        sa.Column("helipad", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("naics_code", sa.String(), nullable=True),
        sa.Column("naics_desc", sa.String(), nullable=True),
        sa.Column("ttl_staff", sa.Integer(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hospitals_geom", "hospitals", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("ix_hospitals_hifld_id"), "hospitals", ["hifld_id"], unique=False)
    op.create_index(op.f("ix_hospitals_name"), "hospitals", ["name"], unique=False)
    op.create_index(op.f("ix_hospitals_objectid"), "hospitals", ["objectid"], unique=False)
    op.create_table(
        "llm_photo_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("photos_hash", sa.String(length=64), nullable=False),
        sa.Column("visual_quality_score", sa.Integer(), nullable=True),
        sa.Column("visual_reasoning", sa.Text(), nullable=True),
        sa.Column("detected_features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("renovation_level", sa.String(), nullable=True),
        sa.Column("raw_response", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "listing_id", "model_name", "model_version", name="uq_llm_photo_score_listing_model"
        ),
    )
    op.create_index(
        op.f("ix_llm_photo_scores_listing_id"), "llm_photo_scores", ["listing_id"], unique=False
    )
    op.create_table(
        "llm_quality_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("description_hash", sa.String(length=64), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("quality_reasoning", sa.Text(), nullable=True),
        sa.Column("positive_factors", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("negative_factors", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_response", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "listing_id", "model_name", "model_version", name="uq_llm_score_listing_model"
        ),
    )
    op.create_index(
        op.f("ix_llm_quality_scores_listing_id"), "llm_quality_scores", ["listing_id"], unique=False
    )
    op.create_table(
        "nat_gas_pipelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("pipe_type", sa.String(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nat_gas_pipelines_geom",
        "nat_gas_pipelines",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_nat_gas_pipelines_objectid"), "nat_gas_pipelines", ["objectid"], unique=False
    )
    op.create_table(
        "nces_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nces_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("school_level", sa.String(), nullable=True),
        sa.Column("grades_low", sa.String(), nullable=True),
        sa.Column("grades_high", sa.String(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("extras", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nces_schools_nces_id"), "nces_schools", ["nces_id"], unique=True)
    op.create_table(
        "noises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("noise_min_db", sa.Integer(), nullable=False),
        sa.Column("noise_max_db", sa.Integer(), nullable=True),
        sa.Column("noise_band", sa.String(), nullable=False),
        sa.Column("source_layer", sa.String(), nullable=False),
        sa.Column("area_sq_m", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_noises_geom", "noises", ["geom"], unique=False, postgresql_using="gist")
    op.create_index("ix_noises_noise_min_db", "noises", ["noise_min_db"], unique=False)
    op.create_table(
        "petroleum_pipelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("pipe_name", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_petroleum_pipelines_geom",
        "petroleum_pipelines",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_petroleum_pipelines_objectid"), "petroleum_pipelines", ["objectid"], unique=False
    )
    op.create_table(
        "place_names",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_type", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_type", "value", name="uq_place_name_type_value"),
    )
    op.create_index(
        "ix_place_names_value_trgm",
        "place_names",
        ["value"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
    )
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("alternate_categories", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("operating_status", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("postcode", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("brand_wikidata", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("social", sa.String(), nullable=True),
        sa.Column("source_dataset", sa.String(), nullable=True),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_places_category", "places", ["category"], unique=False)
    op.create_index("ix_places_geom", "places", ["geom"], unique=False, postgresql_using="gist")
    op.create_index("ix_places_name", "places", ["name"], unique=False)
    op.create_index(op.f("ix_places_source_id"), "places", ["source_id"], unique=True)
    op.create_index("ix_places_state", "places", ["state"], unique=False)
    op.create_table(
        "police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("crime_code", sa.String(), nullable=True),
        sa.Column("crime_group", sa.String(), nullable=True),
        sa.Column("crime_category", sa.String(), nullable=True),
        sa.Column("offense_class", sa.String(), nullable=True),
        sa.Column("crime_description", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("date_of_incident", sa.Date(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index(
        "ix_police_incidents_crime_category", "police_incidents", ["crime_category"], unique=False
    )
    op.create_index(
        "ix_police_incidents_date_of_incident",
        "police_incidents",
        ["date_of_incident"],
        unique=False,
    )
    op.create_index(
        "ix_police_incidents_location",
        "police_incidents",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_police_incidents_offense_class", "police_incidents", ["offense_class"], unique=False
    )
    op.create_table(
        "power_plants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("plant_code", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("utility_name", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("primary_source", sa.String(), nullable=True),
        sa.Column("install_mw", sa.Float(), nullable=True),
        sa.Column("total_mw", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_power_plants_geom", "power_plants", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("ix_power_plants_name"), "power_plants", ["name"], unique=False)
    op.create_index(op.f("ix_power_plants_objectid"), "power_plants", ["objectid"], unique=False)
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("assessed_value", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_properties_parcel_id"), "properties", ["parcel_id"], unique=True)
    op.create_table(
        "property_history_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("township_geoid", sa.String(length=10), nullable=False),
        sa.Column("metric_month", sa.Date(), nullable=False),
        sa.Column("avg_days_on_market_1m", sa.Float(), nullable=True),
        sa.Column("avg_days_on_market_3m", sa.Float(), nullable=True),
        sa.Column("avg_days_on_market_1y", sa.Float(), nullable=True),
        sa.Column("median_sale_price_1m", sa.Float(), nullable=True),
        sa.Column("median_sale_price_3m", sa.Float(), nullable=True),
        sa.Column("median_sale_price_1y", sa.Float(), nullable=True),
        sa.Column("sample_count_1m", sa.Integer(), nullable=True),
        sa.Column("sample_count_3m", sa.Integer(), nullable=True),
        sa.Column("sample_count_1y", sa.Integer(), nullable=True),
        sa.Column(
            "built_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("township_geoid", "metric_month", name="uq_phm_township_month"),
    )
    op.create_index("ix_phm_month", "property_history_metrics", ["metric_month"], unique=False)
    op.create_index("ix_phm_township", "property_history_metrics", ["township_geoid"], unique=False)
    op.create_table(
        "property_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("assigned", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("distance_miles", sa.Float(), nullable=True),
        sa.Column("drive_minutes", sa.Integer(), nullable=True),
        sa.Column("walk_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_property_schools_property_id"), "property_schools", ["property_id"], unique=False
    )
    op.create_index(
        op.f("ix_property_schools_school_id"), "property_schools", ["school_id"], unique=False
    )
    op.create_index(
        "uq_property_school", "property_schools", ["property_id", "school_id"], unique=True
    )
    op.create_table(
        "property_valuations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("confidence_low", sa.Float(), nullable=True),
        sa.Column("confidence_high", sa.Float(), nullable=True),
        sa.Column(
            "estimated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_property_valuations_property_source",
        "property_valuations",
        ["property_id", "source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_valuations_property_id"),
        "property_valuations",
        ["property_id"],
        unique=False,
    )
    op.create_table(
        "railroads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fraarcid", sa.Integer(), nullable=True),
        sa.Column("rrowner1", sa.String(), nullable=True),
        sa.Column("rrowner2", sa.String(), nullable=True),
        sa.Column("rrowner3", sa.String(), nullable=True),
        sa.Column("stateab", sa.String(length=2), nullable=True),
        sa.Column("cntyfips", sa.String(length=5), nullable=True),
        sa.Column("subdivision", sa.String(), nullable=True),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("passngr", sa.String(), nullable=True),
        sa.Column("tracks", sa.Integer(), nullable=True),
        sa.Column("miles", sa.Float(), nullable=True),
        sa.Column("net", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_railroads_fraarcid"), "railroads", ["fraarcid"], unique=True)
    op.create_index(
        "ix_railroads_geom", "railroads", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_table(
        "redfin_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("street_address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("listing_status", sa.String(), nullable=True),
        sa.Column("sold_date", sa.DateTime(), nullable=True),
        sa.Column("sold_price", sa.Float(), nullable=True),
        sa.Column("listing_price", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flood_factor", sa.String(), nullable=True),
        sa.Column("fire_factor", sa.String(), nullable=True),
        sa.Column("flood_score", sa.Integer(), nullable=True),
        sa.Column("fire_score", sa.Integer(), nullable=True),
        sa.Column("has_garage", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("num_garage_spaces", sa.Integer(), nullable=True),
        sa.Column("parking_type", sa.String(), nullable=True),
        sa.Column("garage_entry", sa.String(), nullable=True),
        sa.Column("driveway_surface", sa.String(), nullable=True),
        sa.Column("has_workshop", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_circular_driveway", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_ev_charging", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("num_parking_spaces", sa.Integer(), nullable=True),
        sa.Column("has_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_outdoor_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_primary_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_architectural_fireplace",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("fireplace_fuel_source", sa.String(), nullable=True),
        sa.Column("num_fireplaces", sa.Integer(), nullable=True),
        sa.Column("water_heater_energy_source", sa.String(), nullable=True),
        sa.Column("cooktop_energy_source", sa.String(), nullable=True),
        sa.Column("oven_energy_source", sa.String(), nullable=True),
        sa.Column("has_drink_fridge", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_stainless_appliances", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("appliances_included_count", sa.Integer(), nullable=True),
        sa.Column(
            "has_efficient_windows", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_skylights", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_bay_window", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("laundry_location", sa.String(), nullable=True),
        sa.Column("has_laundry_room", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_utility_sink", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("countertop_material", sa.String(), nullable=True),
        sa.Column(
            "is_primary_downstairs", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_guest_suite", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_butler_pantry", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_walkin_closets", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_tall_ceilings", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_luxury_ceilings", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_sauna", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_bar", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_second_primary", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_room_over_garage", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_open_floorplan", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("is_carpet_free", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_premium_stone", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_hardwood", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_crawl_space", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("facade_type", sa.String(), nullable=True),
        sa.Column("building_area", sa.Float(), nullable=True),
        sa.Column("above_grade_finished_area", sa.Float(), nullable=True),
        sa.Column("below_grade_finished_area", sa.Float(), nullable=True),
        sa.Column("num_stories", sa.Float(), nullable=True),
        sa.Column("lot_size", sa.Float(), nullable=True),
        sa.Column("is_waterfront", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("buyer_financing", sa.String(), nullable=True),
        sa.Column("is_septic", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_well_water", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("no_heating", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("no_cooling", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_hoa", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("association_fee", sa.Float(), nullable=True),
        sa.Column("hoa_name", sa.String(), nullable=True),
        sa.Column(
            "has_enclosed_porch", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_front_porch", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_fenced_yard", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_outdoor_kitchen", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_sport_court", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_private_pool", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_community_pool", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_clubhouse", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_exterior_storage", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_garden", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("num_beds", sa.Integer(), nullable=True),
        sa.Column("num_baths", sa.Float(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("price_per_sqft", sa.Float(), nullable=True),
        sa.Column("listing_agent", sa.String(), nullable=True),
        sa.Column("listing_brokerage", sa.String(), nullable=True),
        sa.Column("buying_agent", sa.String(), nullable=True),
        sa.Column("buying_brokerage", sa.String(), nullable=True),
        sa.Column("apn", sa.String(), nullable=True),
        sa.Column("contract_date", sa.DateTime(), nullable=True),
        sa.Column("property_details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("property_photos", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("redfin_url", sa.String(), nullable=True),
        sa.Column("staging_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("schools_built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("features_built_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_redfin_listings_street_address"),
        "redfin_listings",
        ["street_address"],
        unique=False,
    )
    op.create_index(
        "uq_redfin_listings_address",
        "redfin_listings",
        ["street_address", "city", "state", "zip_code"],
        unique=True,
    )
    op.create_table(
        "redfin_property_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("redfin_school_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_redfin_property_schools_property_id"),
        "redfin_property_schools",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_redfin_property_schools_redfin_school_id"),
        "redfin_property_schools",
        ["redfin_school_id"],
        unique=False,
    )
    op.create_index(
        "uq_redfin_property_school",
        "redfin_property_schools",
        ["property_id", "redfin_school_id"],
        unique=True,
    )
    op.create_table(
        "redfin_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("grades", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "risk_boundaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("infrastructure_type", sa.String(), nullable=False),
        sa.Column("infrastructure_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                srid=4326, dimension=2, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column(
            "built_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_risk_boundaries_geom",
        "risk_boundaries",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_risk_boundaries_infra",
        "risk_boundaries",
        ["infrastructure_type", "infrastructure_id"],
        unique=False,
    )
    op.create_table(
        "roads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("linearid", sa.String(length=22), nullable=True),
        sa.Column("fullname", sa.String(length=100), nullable=True),
        sa.Column("rttyp", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roads_geom", "roads", ["geom"], unique=False, postgresql_using="gist")
    op.create_index(op.f("ix_roads_linearid"), "roads", ["linearid"], unique=True)
    op.create_table(
        "sale_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sale_history_property_id"), "sale_history", ["property_id"], unique=False
    )
    op.create_table(
        "school_districts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("district_type", sa.String(length=10), nullable=True),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("geoid", sa.String(length=7), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("lograde", sa.String(length=2), nullable=True),
        sa.Column("higrade", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("sdtyp", sa.String(length=1), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_school_districts_district_type"),
        "school_districts",
        ["district_type"],
        unique=False,
    )
    op.create_index(op.f("ix_school_districts_geoid"), "school_districts", ["geoid"], unique=False)
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nces_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("school_level", sa.String(), nullable=True),
        sa.Column("grades", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("enrollment", sa.Integer(), nullable=True),
        sa.Column("teachers", sa.Float(), nullable=True),
        sa.Column("student_teacher_ratio", sa.Float(), nullable=True),
        sa.Column("free_lunch_eligible", sa.Integer(), nullable=True),
        sa.Column("reduced_lunch_eligible", sa.Integer(), nullable=True),
        sa.Column("total_frl_eligible", sa.Integer(), nullable=True),
        sa.Column("pct_frl_eligible", sa.Float(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schools_district_id"), "schools", ["district_id"], unique=False)
    op.create_index(op.f("ix_schools_nces_id"), "schools", ["nces_id"], unique=True)
    op.create_table(
        "staging_cary_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_id", sa.String(), nullable=True),
        sa.Column("incident_number", sa.String(), nullable=True),
        sa.Column("crime_category", sa.String(), nullable=True),
        sa.Column("crime_type", sa.String(), nullable=True),
        sa.Column("ucr", sa.String(), nullable=True),
        sa.Column("map_reference", sa.String(), nullable=True),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("from_time", sa.String(), nullable=True),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("to_time", sa.String(), nullable=True),
        sa.Column("crimeday", sa.String(), nullable=True),
        sa.Column("geocode", sa.String(), nullable=True),
        sa.Column("location_category", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("beat_number", sa.String(), nullable=True),
        sa.Column("neighborhd_id", sa.String(), nullable=True),
        sa.Column("apartment_complex", sa.String(), nullable=True),
        sa.Column("residential_subdivision", sa.String(), nullable=True),
        sa.Column("subdivisn_id", sa.String(), nullable=True),
        sa.Column("activity_date", sa.String(), nullable=True),
        sa.Column("phxrecordstatus", sa.String(), nullable=True),
        sa.Column("phxcommunity", sa.String(), nullable=True),
        sa.Column("phxstatus", sa.String(), nullable=True),
        sa.Column("record", sa.String(), nullable=True),
        sa.Column("offensecategory", sa.String(), nullable=True),
        sa.Column("violentproperty", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column("domestic", sa.String(), nullable=True),
        sa.Column("total_incidents", sa.String(), nullable=True),
        sa.Column("year", sa.String(), nullable=True),
        sa.Column("older_than_five_years_from_now", sa.String(), nullable=True),
        sa.Column("chrgcnt", sa.String(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staging_cary_police_incidents_api_id"),
        "staging_cary_police_incidents",
        ["api_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staging_cary_police_incidents_incident_number"),
        "staging_cary_police_incidents",
        ["incident_number"],
        unique=False,
    )
    op.create_table(
        "staging_morrisville_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("inci_id", sa.String(), nullable=True),
        sa.Column("offense", sa.String(), nullable=True),
        sa.Column("date_rept", sa.String(), nullable=True),
        sa.Column("date_occu", sa.String(), nullable=True),
        sa.Column("dow1", sa.String(), nullable=True),
        sa.Column("monthstamp", sa.String(), nullable=True),
        sa.Column("yearstamp", sa.String(), nullable=True),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip", sa.String(), nullable=True),
        sa.Column("neighborhd", sa.String(), nullable=True),
        sa.Column("subdivisn", sa.String(), nullable=True),
        sa.Column("tract", sa.String(), nullable=True),
        sa.Column("zone", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("asst_offcr", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staging_morrisville_police_incidents_inci_id"),
        "staging_morrisville_police_incidents",
        ["inci_id"],
        unique=False,
    )
    op.create_table(
        "staging_noises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("noise_min_db", sa.Integer(), nullable=False),
        sa.Column("noise_max_db", sa.Integer(), nullable=True),
        sa.Column("noise_band", sa.String(), nullable=False),
        sa.Column("source_layer", sa.String(), nullable=False),
        sa.Column("area_sq_m", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "staging_places",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("alternate_categories", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("operating_status", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("postcode", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("brand_wikidata", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("social", sa.String(), nullable=True),
        sa.Column("source_dataset", sa.String(), nullable=True),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "staging_raleigh_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.String(), nullable=True),
        sa.Column("global_id", sa.String(), nullable=True),
        sa.Column("case_number", sa.String(), nullable=True),
        sa.Column("crime_category", sa.String(), nullable=True),
        sa.Column("crime_code", sa.String(), nullable=True),
        sa.Column("crime_description", sa.String(), nullable=True),
        sa.Column("crime_type", sa.String(), nullable=True),
        sa.Column("reported_block_address", sa.String(), nullable=True),
        sa.Column("city_of_incident", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("reported_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_year", sa.Integer(), nullable=True),
        sa.Column("reported_month", sa.Integer(), nullable=True),
        sa.Column("reported_day", sa.Integer(), nullable=True),
        sa.Column("reported_hour", sa.Integer(), nullable=True),
        sa.Column("reported_dayofwk", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("agency", sa.String(), nullable=True),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staging_raleigh_police_incidents_case_number"),
        "staging_raleigh_police_incidents",
        ["case_number"],
        unique=False,
    )
    op.create_table(
        "staging_redfin_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("listing_status", sa.String(), nullable=True),
        sa.Column("sold_date", sa.String(), nullable=True),
        sa.Column("sold_price", sa.String(), nullable=True),
        sa.Column("listing_price", sa.String(), nullable=True),
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Float(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("lot_size", sa.String(), nullable=True),
        sa.Column("price_per_sqft", sa.String(), nullable=True),
        sa.Column("listing_agent", sa.String(), nullable=True),
        sa.Column("listing_brokerage", sa.String(), nullable=True),
        sa.Column("buying_agent", sa.String(), nullable=True),
        sa.Column("buying_brokerage", sa.String(), nullable=True),
        sa.Column("redfin_estimate", sa.String(), nullable=True),
        sa.Column("sale_history", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("tax_history", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("property_details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("schools", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("climate_flood_factor", sa.String(), nullable=True),
        sa.Column("climate_fire_factor", sa.String(), nullable=True),
        sa.Column("photo_s3_paths", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("redfin_url", sa.String(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("extracted_at", sa.Date(), nullable=True),
        sa.Column("is_processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staging_redfin_listings_address"),
        "staging_redfin_listings",
        ["address"],
        unique=False,
    )
    op.create_index(
        "ix_staging_unprocessed",
        "staging_redfin_listings",
        ["id"],
        unique=False,
        postgresql_where=sa.text("is_processed = false"),
    )
    op.create_table(
        "staging_wake_county_property_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_1", sa.String(length=35), nullable=True),
        sa.Column("owner_2", sa.String(length=35), nullable=True),
        sa.Column("address_1", sa.String(length=35), nullable=True),
        sa.Column("address_2", sa.String(length=35), nullable=True),
        sa.Column("address_3", sa.String(length=35), nullable=True),
        sa.Column("reid", sa.String(length=7), nullable=True),
        sa.Column("card_num", sa.String(length=3), nullable=True),
        sa.Column("num_cards", sa.String(length=3), nullable=True),
        sa.Column("street_num", sa.String(length=6), nullable=True),
        sa.Column("street_prefix", sa.String(length=2), nullable=True),
        sa.Column("street_name", sa.String(length=25), nullable=True),
        sa.Column("street_type", sa.String(length=4), nullable=True),
        sa.Column("street_suffix", sa.String(length=2), nullable=True),
        sa.Column("street_misc", sa.String(length=2), nullable=True),
        sa.Column("planning_jurisdiction", sa.String(length=2), nullable=True),
        sa.Column("township", sa.String(length=2), nullable=True),
        sa.Column("fire_district", sa.String(length=2), nullable=True),
        sa.Column("physical_city", sa.String(length=50), nullable=True),
        sa.Column("physical_zip_code", sa.String(length=5), nullable=True),
        sa.Column("city", sa.String(length=3), nullable=True),
        sa.Column("parcel_identification", sa.String(length=19), nullable=True),
        sa.Column("billing_class", sa.String(length=1), nullable=True),
        sa.Column("land_classification", sa.String(length=1), nullable=True),
        sa.Column("zoning", sa.String(length=5), nullable=True),
        sa.Column("deeded_acreage", sa.Float(), nullable=True),
        sa.Column("special_district_1", sa.String(length=3), nullable=True),
        sa.Column("special_district_2", sa.String(length=3), nullable=True),
        sa.Column("special_district_3", sa.String(length=3), nullable=True),
        sa.Column("land_sale_price", sa.Float(), nullable=True),
        sa.Column("land_sale_date", sa.String(length=10), nullable=True),
        sa.Column("total_sale_price", sa.Float(), nullable=True),
        sa.Column("total_sale_date", sa.String(length=10), nullable=True),
        sa.Column("assessed_building_value", sa.Float(), nullable=True),
        sa.Column("assessed_land_value", sa.Float(), nullable=True),
        sa.Column("deed_book", sa.String(length=6), nullable=True),
        sa.Column("deed_page", sa.String(length=6), nullable=True),
        sa.Column("deed_date", sa.String(length=10), nullable=True),
        sa.Column("property_description", sa.String(length=40), nullable=True),
        sa.Column("vcs", sa.String(length=7), nullable=True),
        sa.Column("property_index", sa.String(length=40), nullable=True),
        sa.Column("type_use", sa.String(length=3), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("num_rooms", sa.Integer(), nullable=True),
        sa.Column("units", sa.Integer(), nullable=True),
        sa.Column("heated_area", sa.Float(), nullable=True),
        sa.Column("utilities", sa.String(length=3), nullable=True),
        sa.Column("street_pavement", sa.String(length=1), nullable=True),
        sa.Column("topography", sa.String(length=1), nullable=True),
        sa.Column("year_of_addition", sa.Integer(), nullable=True),
        sa.Column("effective_year", sa.Integer(), nullable=True),
        sa.Column("remodeled_year", sa.Integer(), nullable=True),
        sa.Column("unused", sa.String(length=2), nullable=True),
        sa.Column("special_write_in", sa.String(length=8), nullable=True),
        sa.Column("story_height", sa.String(length=1), nullable=True),
        sa.Column("design_style", sa.String(length=1), nullable=True),
        sa.Column("foundation_basement", sa.String(length=1), nullable=True),
        sa.Column("foundation_basement_pct", sa.String(length=2), nullable=True),
        sa.Column("exterior_wall", sa.String(length=1), nullable=True),
        sa.Column("common_wall", sa.String(length=1), nullable=True),
        sa.Column("roof", sa.String(length=1), nullable=True),
        sa.Column("roof_floor_system", sa.String(length=1), nullable=True),
        sa.Column("floor_finish", sa.String(length=1), nullable=True),
        sa.Column("interior_finish", sa.String(length=1), nullable=True),
        sa.Column("interior_finish_1", sa.String(length=1), nullable=True),
        sa.Column("interior_finish_1_pct", sa.String(length=2), nullable=True),
        sa.Column("interior_finish_2", sa.String(length=1), nullable=True),
        sa.Column("interior_finish_2_pct", sa.String(length=2), nullable=True),
        sa.Column("heat", sa.String(length=1), nullable=True),
        sa.Column("heat_pct", sa.String(length=2), nullable=True),
        sa.Column("air", sa.String(length=1), nullable=True),
        sa.Column("air_pct", sa.String(length=2), nullable=True),
        sa.Column("bath", sa.String(length=1), nullable=True),
        sa.Column("bath_fixtures", sa.String(length=3), nullable=True),
        sa.Column("builtin_1_description", sa.String(length=15), nullable=True),
        sa.Column("builtin_2_description", sa.String(length=15), nullable=True),
        sa.Column("builtin_3_description", sa.String(length=15), nullable=True),
        sa.Column("builtin_4_description", sa.String(length=15), nullable=True),
        sa.Column("builtin_5_description", sa.String(length=15), nullable=True),
        sa.Column("grade", sa.String(length=5), nullable=True),
        sa.Column("assessed_grade_difference", sa.String(length=3), nullable=True),
        sa.Column("accrued_assessed_condition_pct", sa.String(length=3), nullable=True),
        sa.Column("land_deferred_code", sa.String(length=1), nullable=True),
        sa.Column("land_deferred_amount", sa.Float(), nullable=True),
        sa.Column("historic_deferred_code", sa.String(length=1), nullable=True),
        sa.Column("historic_deferred_amount", sa.Float(), nullable=True),
        sa.Column("recycled_units", sa.Integer(), nullable=True),
        sa.Column("disqualifying_qualifying_flags", sa.String(length=1), nullable=True),
        sa.Column("land_disqualify_qualify_flag", sa.String(length=1), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staging_wake_county_property_data_reid"),
        "staging_wake_county_property_data",
        ["reid"],
        unique=False,
    )
    op.create_table(
        "subdivisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("county_fips", sa.String(length=5), nullable=False),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("lots", sa.Integer(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "built_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("county_fips", "source_id", name="uq_subdivisions_county_source"),
    )
    op.create_index("ix_subdivisions_county_fips", "subdivisions", ["county_fips"], unique=False)
    op.create_index(
        "ix_subdivisions_geom", "subdivisions", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index("ix_subdivisions_name", "subdivisions", ["name"], unique=False)
    op.create_table(
        "tax_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("property_tax", sa.Float(), nullable=True),
        sa.Column("assessment_value_land", sa.Float(), nullable=True),
        sa.Column("assessment_value_additions", sa.Float(), nullable=True),
        sa.Column("assessment_value", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tax_history_property_id"), "tax_history", ["property_id"], unique=False
    )
    op.create_table(
        "townships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("cousubfp", sa.String(length=5), nullable=True),
        sa.Column("cousubns", sa.String(length=8), nullable=True),
        sa.Column("geoid", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("classfp", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("cnectafp", sa.String(length=3), nullable=True),
        sa.Column("nectafp", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_townships_geoid"), "townships", ["geoid"], unique=False)
    op.create_table(
        "tracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("tractce", sa.String(length=6), nullable=True),
        sa.Column("geoid", sa.String(length=11), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tracts_geoid"), "tracts", ["geoid"], unique=False)
    op.create_table(
        "trails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("permanentidentifier", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("trail_type", sa.String(), nullable=True),
        sa.Column("length_miles", sa.Float(), nullable=True),
        sa.Column("maintainer", sa.String(), nullable=True),
        sa.Column("national_designation", sa.String(), nullable=True),
        sa.Column("hiker_pedestrian", sa.String(), nullable=True),
        sa.Column("bicycle", sa.String(), nullable=True),
        sa.Column("pack_saddle", sa.String(), nullable=True),
        sa.Column("atv", sa.String(), nullable=True),
        sa.Column("motorcycle", sa.String(), nullable=True),
        sa.Column("ohv_over_50_inches", sa.String(), nullable=True),
        sa.Column("snowshoe", sa.String(), nullable=True),
        sa.Column("cross_country_ski", sa.String(), nullable=True),
        sa.Column("dogsled", sa.String(), nullable=True),
        sa.Column("snowmobile", sa.String(), nullable=True),
        sa.Column("non_motorized_watercraft", sa.String(), nullable=True),
        sa.Column("motorized_watercraft", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trails_geom", "trails", ["geom"], unique=False, postgresql_using="gist")
    op.create_index(op.f("ix_trails_name"), "trails", ["name"], unique=False)
    op.create_index(
        op.f("ix_trails_permanentidentifier"), "trails", ["permanentidentifier"], unique=True
    )
    op.create_table(
        "transmission_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("line_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("voltage", sa.Float(), nullable=True),
        sa.Column("volt_class", sa.String(), nullable=True),
        sa.Column("sub_1", sa.String(), nullable=True),
        sa.Column("sub_2", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transmission_lines_geom",
        "transmission_lines",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_transmission_lines_objectid"), "transmission_lines", ["objectid"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("oauth_id", sa.String(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "wake_subdivisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=40), nullable=True),
        sa.Column("snumber", sa.String(length=10), nullable=True),
        sa.Column("access_rd", sa.String(length=30), nullable=True),
        sa.Column("jurisdiction", sa.String(length=25), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("lots", sa.Integer(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("mapclass", sa.Integer(), nullable=True),
        sa.Column("iscluster", sa.String(length=5), nullable=True),
        sa.Column("approvdate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appldate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_edited_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_wake_subdivisions_objectid"), "wake_subdivisions", ["objectid"], unique=False
    )
    op.create_index(
        op.f("ix_wake_subdivisions_snumber"), "wake_subdivisions", ["snumber"], unique=False
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False)
    op.create_table(
        "property_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_hash", sa.String(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["redfin_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_features_computed_at", "property_features", ["computed_at"], unique=False
    )
    op.create_index(
        op.f("ix_property_features_property_id"), "property_features", ["property_id"], unique=True
    )
    op.create_table(
        "property_geo_lookups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("census_tract_geoid", sa.String(length=11), nullable=True),
        sa.Column("census_block_group_geoid", sa.String(length=12), nullable=True),
        sa.Column("county_subdivision_geoid", sa.String(length=10), nullable=True),
        sa.Column("county_geoid", sa.String(length=5), nullable=True),
        sa.Column("subdivision_id", sa.Integer(), nullable=True),
        sa.Column("subdivision_name", sa.String(), nullable=True),
        sa.Column("in_noise_zone", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("noise_max_db", sa.Integer(), nullable=True),
        sa.Column("noise_source_layers", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("in_risk_zone", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("risk_max_severity", sa.String(), nullable=True),
        sa.Column("risk_types", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("school_district_geoid", sa.String(length=7), nullable=True),
        sa.Column("dist_nearest_school_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_elementary_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_middle_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_high_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_park_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_greenway_m", sa.Float(), nullable=True),
        sa.Column("dist_nearest_hospital_m", sa.Float(), nullable=True),
        sa.Column("avg_school_rating", sa.Float(), nullable=True),
        sa.Column("avg_school_drive", sa.Float(), nullable=True),
        sa.Column(
            "in_critical_risk_zone", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "built_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["property_id"], ["redfin_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_geo_lookups_bg",
        "property_geo_lookups",
        ["census_block_group_geoid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_geo_lookups_property_id"),
        "property_geo_lookups",
        ["property_id"],
        unique=True,
    )
    op.create_index(
        "ix_property_geo_lookups_tract",
        "property_geo_lookups",
        ["census_tract_geoid"],
        unique=False,
    )
    op.create_table(
        "property_shap_values",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("shap_values", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("base_value", sa.Float(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["property_id"], ["redfin_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "model_version", name="uq_property_shap_prop_version"),
    )
    op.create_index(
        op.f("ix_property_shap_values_property_id"),
        "property_shap_values",
        ["property_id"],
        unique=False,
    )
    op.create_table(
        "saved_pois",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("match_type", sa.String(), nullable=False),
        sa.Column("match_value", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("user_category", sa.String(), nullable=True),
        sa.Column("marker_color", sa.String(length=7), nullable=True),
        sa.Column("marker_image_url", sa.String(), nullable=True),
        sa.Column(
            "alternate_names",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "match_type", "match_value", name="uq_saved_poi_user_match"),
    )
    op.create_index(op.f("ix_saved_pois_user_id"), "saved_pois", ["user_id"], unique=False)
    op.create_table(
        "saved_properties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["redfin_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_saved_property_user_listing"),
    )
    op.create_index(
        op.f("ix_saved_properties_listing_id"), "saved_properties", ["listing_id"], unique=False
    )
    op.create_index(
        op.f("ix_saved_properties_user_id"), "saved_properties", ["user_id"], unique=False
    )
    # -- Demographic views --------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_tract_demographics AS
        SELECT t.id, t.geoid, t.geom,
               COALESCE(t.namelsad, t.name, t.geoid) AS name,
               {_DEMO_COLS},
               {_ASIAN_SUB}
        FROM tracts t
        LEFT JOIN acs_demographics d
            ON t.geoid = d.geoid
           AND d.geography_level = 'tract'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'tract'
           )
        {_asian_lateral("tract", "t.geoid")}
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW v_block_group_demographics AS
        SELECT bg.id, bg.geoid, bg.geom,
               COALESCE(bg.namelsad, bg.geoid) AS name,
               {_DEMO_COLS},
               {_ASIAN_SUB}
        FROM block_groups bg
        LEFT JOIN acs_demographics d
            ON bg.geoid = d.geoid
           AND d.geography_level = 'block_group'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'block_group'
           )
        {_asian_lateral("block_group", "bg.geoid")}
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW v_county_demographics AS
        SELECT c.id, c.geoid, c.geom,
               COALESCE(c.namelsad, c.name, c.geoid) AS name,
               {_DEMO_COLS},
               {_ASIAN_SUB}
        FROM counties c
        LEFT JOIN acs_demographics d
            ON c.geoid = d.geoid
           AND d.geography_level = 'county'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'county'
           )
        {_asian_lateral("county", "c.geoid")}
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW v_township_demographics AS
        SELECT tw.id, tw.geoid, tw.geom,
               COALESCE(tw.namelsad, tw.name, tw.geoid) AS name,
               {_DEMO_COLS},
               {_ASIAN_SUB}
        FROM townships tw
        LEFT JOIN acs_demographics d
            ON tw.geoid = d.geoid
           AND d.geography_level = 'county_subdivision'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'county_subdivision'
           )
        {_asian_lateral("county_subdivision", "tw.geoid")}
    """)

    op.execute(f"""
        CREATE OR REPLACE VIEW v_subdivision_demographics AS
        SELECT s.id,
               ('subdiv_' || s.id::text) AS geoid,
               s.geom,
               COALESCE(s.name, 'Subdivision ' || s.id::text) AS name,
               {_DEMO_COLS},
               {_ASIAN_SUB}
        FROM subdivisions s
        LEFT JOIN acs_demographics d
            ON d.geoid = 'subdiv_' || s.id::text
           AND d.geography_level = 'subdivision'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'subdivision'
           )
        {_asian_lateral("subdivision", "'subdiv_' || s.id::text")}
    """)

    # -- Label point views ---------------------------------------------------
    _label_views = {
        "v_tract_labels": "v_tract_demographics",
        "v_block_group_labels": "v_block_group_demographics",
        "v_county_labels": "v_county_demographics",
        "v_township_labels": "v_township_demographics",
        "v_subdivision_labels": "v_subdivision_demographics",
    }
    for label_view, source_view in _label_views.items():
        op.execute(f"""
            CREATE OR REPLACE VIEW {label_view} AS
            SELECT id, geoid,
                   ST_PointOnSurface(geom) AS geom,
                   name,
                   population,
                   median_income,
                   median_age,
                   home_ownership_rate,
                   pct_white, pct_black, pct_hispanic, pct_asian, pct_other,
                   dominant_race, dominant_race_pct,
                   dominant_asian_subgroup, dominant_asian_subgroup_pct,
                   pct_asian_indian, pct_chinese, pct_filipino,
                   pct_japanese, pct_korean, pct_vietnamese, pct_other_asian
            FROM {source_view}
        """)

    # -- Infrastructure view -------------------------------------------------
    op.execute("""
        CREATE OR REPLACE VIEW v_infrastructure AS
        SELECT id::text AS feature_id, 'cell_tower' AS infra_type, geom,
               NULL::text AS name
        FROM cell_towers
        UNION ALL
        SELECT id::text, 'transmission_line', geom, NULL
        FROM transmission_lines
        UNION ALL
        SELECT id::text, 'power_plant', geom, name
        FROM power_plants
        UNION ALL
        SELECT id::text, 'nat_gas_pipeline', geom, NULL
        FROM nat_gas_pipelines
        UNION ALL
        SELECT id::text, 'petroleum_pipeline', geom, NULL
        FROM petroleum_pipelines
        UNION ALL
        SELECT id::text, 'railroad', geom, COALESCE(rrowner1, 'Railroad')
        FROM railroads
        UNION ALL
        SELECT id::text, 'airport', geom, name
        FROM airports
        UNION ALL
        SELECT id::text, 'road', geom, fullname
        FROM roads
    """)
    # ### end Alembic commands ###

    # Spatial indexes for schools, school_districts, nces_schools, redfin_listings
    op.create_index(
        "ix_schools_location", "schools", ["location"],
        unique=False, postgresql_using="gist",
    )
    op.create_index(
        "ix_school_districts_geom", "school_districts", ["geom"],
        unique=False, postgresql_using="gist",
    )
    op.create_index(
        "ix_nces_schools_location", "nces_schools", ["location"],
        unique=False, postgresql_using="gist",
    )
    op.create_index(
        "ix_redfin_listings_location", "redfin_listings", ["location"],
        unique=False, postgresql_using="gist",
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Drop views first (they depend on the underlying tables)
    op.execute("DROP VIEW IF EXISTS v_tract_labels")
    op.execute("DROP VIEW IF EXISTS v_block_group_labels")
    op.execute("DROP VIEW IF EXISTS v_county_labels")
    op.execute("DROP VIEW IF EXISTS v_township_labels")
    op.execute("DROP VIEW IF EXISTS v_subdivision_labels")
    op.execute("DROP VIEW IF EXISTS v_tract_demographics")
    op.execute("DROP VIEW IF EXISTS v_block_group_demographics")
    op.execute("DROP VIEW IF EXISTS v_county_demographics")
    op.execute("DROP VIEW IF EXISTS v_township_demographics")
    op.execute("DROP VIEW IF EXISTS v_subdivision_demographics")
    op.execute("DROP VIEW IF EXISTS v_infrastructure")

    op.drop_index(op.f("ix_saved_properties_user_id"), table_name="saved_properties")
    op.drop_index(op.f("ix_saved_properties_listing_id"), table_name="saved_properties")
    op.drop_table("saved_properties")
    op.drop_index(op.f("ix_saved_pois_user_id"), table_name="saved_pois")
    op.drop_table("saved_pois")
    op.drop_index(op.f("ix_property_shap_values_property_id"), table_name="property_shap_values")
    op.drop_table("property_shap_values")
    op.drop_index("ix_property_geo_lookups_tract", table_name="property_geo_lookups")
    op.drop_index(op.f("ix_property_geo_lookups_property_id"), table_name="property_geo_lookups")
    op.drop_index("ix_property_geo_lookups_bg", table_name="property_geo_lookups")
    op.drop_table("property_geo_lookups")
    op.drop_index(op.f("ix_property_features_property_id"), table_name="property_features")
    op.drop_index("ix_property_features_computed_at", table_name="property_features")
    op.drop_table("property_features")
    op.drop_index(op.f("ix_api_keys_user_id"), table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_wake_subdivisions_snumber"), table_name="wake_subdivisions")
    op.drop_index(op.f("ix_wake_subdivisions_objectid"), table_name="wake_subdivisions")
    op.drop_table("wake_subdivisions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_transmission_lines_objectid"), table_name="transmission_lines")
    op.drop_index(
        "ix_transmission_lines_geom", table_name="transmission_lines", postgresql_using="gist"
    )
    op.drop_table("transmission_lines")
    op.drop_index(op.f("ix_trails_permanentidentifier"), table_name="trails")
    op.drop_index(op.f("ix_trails_name"), table_name="trails")
    op.drop_index("ix_trails_geom", table_name="trails", postgresql_using="gist")
    op.drop_table("trails")
    op.drop_index(op.f("ix_tracts_geoid"), table_name="tracts")
    op.drop_table("tracts")
    op.drop_index(op.f("ix_townships_geoid"), table_name="townships")
    op.drop_table("townships")
    op.drop_index(op.f("ix_tax_history_property_id"), table_name="tax_history")
    op.drop_table("tax_history")
    op.drop_index("ix_subdivisions_name", table_name="subdivisions")
    op.drop_index("ix_subdivisions_geom", table_name="subdivisions", postgresql_using="gist")
    op.drop_index("ix_subdivisions_county_fips", table_name="subdivisions")
    op.drop_table("subdivisions")
    op.drop_index(
        op.f("ix_staging_wake_county_property_data_reid"),
        table_name="staging_wake_county_property_data",
    )
    op.drop_table("staging_wake_county_property_data")
    op.drop_index(
        "ix_staging_unprocessed",
        table_name="staging_redfin_listings",
        postgresql_where=sa.text("is_processed = false"),
    )
    op.drop_index(op.f("ix_staging_redfin_listings_address"), table_name="staging_redfin_listings")
    op.drop_table("staging_redfin_listings")
    op.drop_index(
        op.f("ix_staging_raleigh_police_incidents_case_number"),
        table_name="staging_raleigh_police_incidents",
    )
    op.drop_table("staging_raleigh_police_incidents")
    op.drop_table("staging_places")
    op.drop_table("staging_noises")
    op.drop_index(
        op.f("ix_staging_morrisville_police_incidents_inci_id"),
        table_name="staging_morrisville_police_incidents",
    )
    op.drop_table("staging_morrisville_police_incidents")
    op.drop_index(
        op.f("ix_staging_cary_police_incidents_incident_number"),
        table_name="staging_cary_police_incidents",
    )
    op.drop_index(
        op.f("ix_staging_cary_police_incidents_api_id"), table_name="staging_cary_police_incidents"
    )
    op.drop_table("staging_cary_police_incidents")
    op.drop_index(op.f("ix_schools_nces_id"), table_name="schools")
    op.drop_index(op.f("ix_schools_district_id"), table_name="schools")
    op.drop_table("schools")
    op.drop_index(op.f("ix_school_districts_geoid"), table_name="school_districts")
    op.drop_index(op.f("ix_school_districts_district_type"), table_name="school_districts")
    op.drop_table("school_districts")
    op.drop_index(op.f("ix_sale_history_property_id"), table_name="sale_history")
    op.drop_table("sale_history")
    op.drop_index(op.f("ix_roads_linearid"), table_name="roads")
    op.drop_index("ix_roads_geom", table_name="roads", postgresql_using="gist")
    op.drop_table("roads")
    op.drop_index("ix_risk_boundaries_infra", table_name="risk_boundaries")
    op.drop_index("ix_risk_boundaries_geom", table_name="risk_boundaries", postgresql_using="gist")
    op.drop_table("risk_boundaries")
    op.drop_table("redfin_schools")
    op.drop_index("uq_redfin_property_school", table_name="redfin_property_schools")
    op.drop_index(
        op.f("ix_redfin_property_schools_redfin_school_id"), table_name="redfin_property_schools"
    )
    op.drop_index(
        op.f("ix_redfin_property_schools_property_id"), table_name="redfin_property_schools"
    )
    op.drop_table("redfin_property_schools")
    op.drop_index("uq_redfin_listings_address", table_name="redfin_listings")
    op.drop_index(op.f("ix_redfin_listings_street_address"), table_name="redfin_listings")
    op.drop_table("redfin_listings")
    op.drop_index("ix_railroads_geom", table_name="railroads", postgresql_using="gist")
    op.drop_index(op.f("ix_railroads_fraarcid"), table_name="railroads")
    op.drop_table("railroads")
    op.drop_index(op.f("ix_property_valuations_property_id"), table_name="property_valuations")
    op.drop_table("property_valuations")
    op.drop_index("uq_property_school", table_name="property_schools")
    op.drop_index(op.f("ix_property_schools_school_id"), table_name="property_schools")
    op.drop_index(op.f("ix_property_schools_property_id"), table_name="property_schools")
    op.drop_table("property_schools")
    op.drop_index("ix_phm_township", table_name="property_history_metrics")
    op.drop_index("ix_phm_month", table_name="property_history_metrics")
    op.drop_table("property_history_metrics")
    op.drop_index(op.f("ix_properties_parcel_id"), table_name="properties")
    op.drop_table("properties")
    op.drop_index(op.f("ix_power_plants_objectid"), table_name="power_plants")
    op.drop_index(op.f("ix_power_plants_name"), table_name="power_plants")
    op.drop_index("ix_power_plants_geom", table_name="power_plants", postgresql_using="gist")
    op.drop_table("power_plants")
    op.drop_index("ix_police_incidents_offense_class", table_name="police_incidents")
    op.drop_index(
        "ix_police_incidents_location", table_name="police_incidents", postgresql_using="gist"
    )
    op.drop_index("ix_police_incidents_date_of_incident", table_name="police_incidents")
    op.drop_index("ix_police_incidents_crime_category", table_name="police_incidents")
    op.drop_table("police_incidents")
    op.drop_index("ix_places_state", table_name="places")
    op.drop_index(op.f("ix_places_source_id"), table_name="places")
    op.drop_index("ix_places_name", table_name="places")
    op.drop_index("ix_places_geom", table_name="places", postgresql_using="gist")
    op.drop_index("ix_places_category", table_name="places")
    op.drop_table("places")
    op.drop_index(
        "ix_place_names_value_trgm",
        table_name="place_names",
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
    )
    op.drop_table("place_names")
    op.drop_index(op.f("ix_petroleum_pipelines_objectid"), table_name="petroleum_pipelines")
    op.drop_index(
        "ix_petroleum_pipelines_geom", table_name="petroleum_pipelines", postgresql_using="gist"
    )
    op.drop_table("petroleum_pipelines")
    op.drop_index("ix_noises_noise_min_db", table_name="noises")
    op.drop_index("ix_noises_geom", table_name="noises", postgresql_using="gist")
    op.drop_table("noises")
    op.drop_index(op.f("ix_nces_schools_nces_id"), table_name="nces_schools")
    op.drop_table("nces_schools")
    op.drop_index(op.f("ix_nat_gas_pipelines_objectid"), table_name="nat_gas_pipelines")
    op.drop_index(
        "ix_nat_gas_pipelines_geom", table_name="nat_gas_pipelines", postgresql_using="gist"
    )
    op.drop_table("nat_gas_pipelines")
    op.drop_index(op.f("ix_llm_quality_scores_listing_id"), table_name="llm_quality_scores")
    op.drop_table("llm_quality_scores")
    op.drop_index(op.f("ix_llm_photo_scores_listing_id"), table_name="llm_photo_scores")
    op.drop_table("llm_photo_scores")
    op.drop_index(op.f("ix_hospitals_objectid"), table_name="hospitals")
    op.drop_index(op.f("ix_hospitals_name"), table_name="hospitals")
    op.drop_index(op.f("ix_hospitals_hifld_id"), table_name="hospitals")
    op.drop_index("ix_hospitals_geom", table_name="hospitals", postgresql_using="gist")
    op.drop_table("hospitals")
    op.drop_index(op.f("ix_greenspaces_source_id"), table_name="greenspaces")
    op.drop_index(op.f("ix_greenspaces_name"), table_name="greenspaces")
    op.drop_index("ix_greenspaces_geom", table_name="greenspaces", postgresql_using="gist")
    op.drop_table("greenspaces")
    op.drop_index(
        op.f("ix_greenspace_region_metrics_geoid"), table_name="greenspace_region_metrics"
    )
    op.drop_index(
        op.f("ix_greenspace_region_metrics_geo_level"), table_name="greenspace_region_metrics"
    )
    op.drop_table("greenspace_region_metrics")
    op.drop_table("economic_indicators")
    op.drop_index(op.f("ix_data_requests_address"), table_name="data_requests")
    op.drop_table("data_requests")
    op.drop_index(op.f("ix_counties_geoid"), table_name="counties")
    op.drop_table("counties")
    op.drop_index(op.f("ix_cell_towers_objectid"), table_name="cell_towers")
    op.drop_index("ix_cell_towers_geom", table_name="cell_towers", postgresql_using="gist")
    op.drop_table("cell_towers")
    op.drop_index(op.f("ix_blocks_geoid20"), table_name="blocks")
    op.drop_table("blocks")
    op.drop_index(op.f("ix_block_groups_geoid"), table_name="block_groups")
    op.drop_table("block_groups")
    op.drop_index(op.f("ix_airports_name"), table_name="airports")
    op.drop_index(op.f("ix_airports_ident"), table_name="airports")
    op.drop_index("ix_airports_geom", table_name="airports", postgresql_using="gist")
    op.drop_table("airports")
    op.drop_index("ix_acs_detail_race_lookup", table_name="acs_detailed_race")
    op.drop_index("ix_acs_detail_race_category", table_name="acs_detailed_race")
    op.drop_table("acs_detailed_race")
    op.drop_index(op.f("ix_acs_demographics_geoid"), table_name="acs_demographics")
    op.drop_index(op.f("ix_acs_demographics_geography_level"), table_name="acs_demographics")
    op.drop_index(op.f("ix_acs_demographics_acs_year"), table_name="acs_demographics")
    op.drop_table("acs_demographics")

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    # ### end Alembic commands ###
