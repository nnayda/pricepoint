"""Unify ACS demographics into single table

Revision ID: r5t7v9x1z3a5
Revises: q4s6u8w0y2b4
Create Date: 2026-02-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r5t7v9x1z3a5"
down_revision: str | None = "q4s6u8w0y2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create unified acs_demographics table
    op.create_table(
        "acs_demographics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geography_level", sa.String(length=25), nullable=False),
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acs_year", sa.Integer(), nullable=False),
        # Population
        sa.Column("total_population", sa.Integer(), nullable=True),
        sa.Column("male_population", sa.Integer(), nullable=True),
        sa.Column("female_population", sa.Integer(), nullable=True),
        # Age
        sa.Column("pop_under_18", sa.Integer(), nullable=True),
        sa.Column("pop_18_to_22", sa.Integer(), nullable=True),
        sa.Column("pop_23_to_29", sa.Integer(), nullable=True),
        sa.Column("pop_30_to_39", sa.Integer(), nullable=True),
        sa.Column("pop_40_to_49", sa.Integer(), nullable=True),
        sa.Column("pop_50_to_64", sa.Integer(), nullable=True),
        sa.Column("pop_65_plus", sa.Integer(), nullable=True),
        sa.Column("median_age", sa.Float(), nullable=True),
        # Race
        sa.Column("race_white", sa.Integer(), nullable=True),
        sa.Column("race_black", sa.Integer(), nullable=True),
        sa.Column("race_american_indian", sa.Integer(), nullable=True),
        sa.Column("race_asian", sa.Integer(), nullable=True),
        sa.Column("race_pacific_islander", sa.Integer(), nullable=True),
        sa.Column("race_other", sa.Integer(), nullable=True),
        sa.Column("race_two_or_more", sa.Integer(), nullable=True),
        # Hispanic
        sa.Column("hispanic_total", sa.Integer(), nullable=True),
        sa.Column("not_hispanic", sa.Integer(), nullable=True),
        sa.Column("hispanic", sa.Integer(), nullable=True),
        # Income brackets
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
        # Median income
        sa.Column("median_household_income", sa.Integer(), nullable=True),
        # Education
        sa.Column("edu_total", sa.Integer(), nullable=True),
        sa.Column("edu_less_than_hs", sa.Integer(), nullable=True),
        sa.Column("edu_high_school", sa.Integer(), nullable=True),
        sa.Column("edu_some_college", sa.Integer(), nullable=True),
        sa.Column("edu_bachelors", sa.Integer(), nullable=True),
        sa.Column("edu_graduate_plus", sa.Integer(), nullable=True),
        # Home ownership
        sa.Column("housing_total_occupied", sa.Integer(), nullable=True),
        sa.Column("housing_owner_occupied", sa.Integer(), nullable=True),
        sa.Column("housing_renter_occupied", sa.Integer(), nullable=True),
        # Home value
        sa.Column("median_home_value", sa.Integer(), nullable=True),
        # Metadata
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "geography_level", "geoid", "acs_year", name="uq_acs_demo_level_geoid_year"
        ),
    )
    op.create_index("ix_acs_demographics_geography_level", "acs_demographics", ["geography_level"])
    op.create_index("ix_acs_demographics_geoid", "acs_demographics", ["geoid"])
    op.create_index("ix_acs_demographics_acs_year", "acs_demographics", ["acs_year"])

    # 2. Copy data from tract table.
    # Old tables have 5 age buckets (pop_under_18, pop_18_to_34, pop_35_to_54,
    # pop_55_to_64, pop_65_plus). New table has 7 buckets. We copy pop_under_18
    # and pop_65_plus directly, set the 5 new intermediate buckets to NULL since
    # they can't be derived from the coarser old buckets. Data will be re-fetched
    # from the Census API with the correct granularity.
    _COPY_SQL = """
        INSERT INTO acs_demographics (
            geography_level, geoid, name, acs_year,
            total_population, male_population, female_population,
            pop_under_18, pop_65_plus, median_age,
            race_white, race_black, race_american_indian, race_asian,
            race_pacific_islander, race_other, race_two_or_more,
            hispanic_total, not_hispanic, hispanic,
            total_households,
            hh_income_under_10k, hh_income_10k_to_15k, hh_income_15k_to_20k,
            hh_income_20k_to_25k, hh_income_25k_to_30k, hh_income_30k_to_35k,
            hh_income_35k_to_40k, hh_income_40k_to_45k, hh_income_45k_to_50k,
            hh_income_50k_to_60k, hh_income_60k_to_75k, hh_income_75k_to_100k,
            hh_income_100k_to_125k, hh_income_125k_to_150k, hh_income_150k_to_200k,
            hh_income_200k_plus, median_household_income,
            edu_total, edu_less_than_hs, edu_high_school, edu_some_college,
            edu_bachelors, edu_graduate_plus,
            housing_total_occupied, housing_owner_occupied, housing_renter_occupied,
            median_home_value, loaded_at
        )
        SELECT
            '{level}', geoid, name, acs_year,
            total_population, male_population, female_population,
            pop_under_18, pop_65_plus, median_age,
            race_white, race_black, race_american_indian, race_asian,
            race_pacific_islander, race_other, race_two_or_more,
            hispanic_total, not_hispanic, hispanic,
            total_households,
            hh_income_under_10k, hh_income_10k_to_15k, hh_income_15k_to_20k,
            hh_income_20k_to_25k, hh_income_25k_to_30k, hh_income_30k_to_35k,
            hh_income_35k_to_40k, hh_income_40k_to_45k, hh_income_45k_to_50k,
            hh_income_50k_to_60k, hh_income_60k_to_75k, hh_income_75k_to_100k,
            hh_income_100k_to_125k, hh_income_125k_to_150k, hh_income_150k_to_200k,
            hh_income_200k_plus, median_household_income,
            edu_total, edu_less_than_hs, edu_high_school, edu_some_college,
            edu_bachelors, edu_graduate_plus,
            housing_total_occupied, housing_owner_occupied, housing_renter_occupied,
            median_home_value, loaded_at
        FROM {table}
    """
    op.execute(_COPY_SQL.format(level="tract", table="acs_tract_demographics"))

    # 3. Copy data from block group table
    op.execute(_COPY_SQL.format(level="block_group", table="acs_block_group_demographics"))

    # 4. Drop old tables
    op.drop_table("acs_block_group_demographics")
    op.drop_table("acs_tract_demographics")

    # 5. Add GiST spatial index on wake_subdivisions.geom (needed for ST_Intersects)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_wake_subdivisions_geom "
        "ON wake_subdivisions USING gist (geom)"
    )


def downgrade() -> None:
    # Drop spatial index on wake_subdivisions
    op.drop_index("idx_wake_subdivisions_geom", table_name="wake_subdivisions")

    # Recreate old tables
    from r5t7v9x1z3a5_unify_acs_demographics_table import _COL_LIST  # noqa: F401

    # Recreate acs_tract_demographics
    op.execute("""
        CREATE TABLE acs_tract_demographics AS
        SELECT id, geoid::varchar(11) AS geoid, name, acs_year,
               total_population, male_population, female_population,
               pop_under_18, pop_18_to_22, pop_23_to_29, pop_30_to_39,
               pop_40_to_49, pop_50_to_64, pop_65_plus, median_age,
               race_white, race_black, race_american_indian, race_asian,
               race_pacific_islander, race_other, race_two_or_more,
               hispanic_total, not_hispanic, hispanic,
               total_households,
               hh_income_under_10k, hh_income_10k_to_15k, hh_income_15k_to_20k,
               hh_income_20k_to_25k, hh_income_25k_to_30k, hh_income_30k_to_35k,
               hh_income_35k_to_40k, hh_income_40k_to_45k, hh_income_45k_to_50k,
               hh_income_50k_to_60k, hh_income_60k_to_75k, hh_income_75k_to_100k,
               hh_income_100k_to_125k, hh_income_125k_to_150k, hh_income_150k_to_200k,
               hh_income_200k_plus, median_household_income,
               edu_total, edu_less_than_hs, edu_high_school, edu_some_college,
               edu_bachelors, edu_graduate_plus,
               housing_total_occupied, housing_owner_occupied, housing_renter_occupied,
               median_home_value, loaded_at
        FROM acs_demographics WHERE geography_level = 'tract'
    """)

    # Recreate acs_block_group_demographics
    op.execute("""
        CREATE TABLE acs_block_group_demographics AS
        SELECT id, geoid::varchar(12) AS geoid, name, acs_year,
               total_population, male_population, female_population,
               pop_under_18, pop_18_to_22, pop_23_to_29, pop_30_to_39,
               pop_40_to_49, pop_50_to_64, pop_65_plus, median_age,
               race_white, race_black, race_american_indian, race_asian,
               race_pacific_islander, race_other, race_two_or_more,
               hispanic_total, not_hispanic, hispanic,
               total_households,
               hh_income_under_10k, hh_income_10k_to_15k, hh_income_15k_to_20k,
               hh_income_20k_to_25k, hh_income_25k_to_30k, hh_income_30k_to_35k,
               hh_income_35k_to_40k, hh_income_40k_to_45k, hh_income_45k_to_50k,
               hh_income_50k_to_60k, hh_income_60k_to_75k, hh_income_75k_to_100k,
               hh_income_100k_to_125k, hh_income_125k_to_150k, hh_income_150k_to_200k,
               hh_income_200k_plus, median_household_income,
               edu_total, edu_less_than_hs, edu_high_school, edu_some_college,
               edu_bachelors, edu_graduate_plus,
               housing_total_occupied, housing_owner_occupied, housing_renter_occupied,
               median_home_value, loaded_at
        FROM acs_demographics WHERE geography_level = 'block_group'
    """)

    # Drop unified table
    op.drop_table("acs_demographics")
