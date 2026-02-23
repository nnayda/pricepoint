"""Add ACS demographic tables

Revision ID: q4s6u8w0y2b4
Revises: p3r5t7v9x1z3
Create Date: 2026-02-22 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q4s6u8w0y2b4"
down_revision: str | None = "p3r5t7v9x1z3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_acs_table(table_name: str, geoid_length: int, uq_name: str) -> None:
    """Create an ACS demographic table (shared schema for tract / block group)."""
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geoid", sa.String(length=geoid_length), nullable=False),
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
        sa.UniqueConstraint("geoid", "acs_year", name=uq_name),
    )
    op.create_index(f"ix_{table_name}_geoid", table_name, ["geoid"])
    op.create_index(f"ix_{table_name}_acs_year", table_name, ["acs_year"])


def upgrade() -> None:
    _create_acs_table("acs_tract_demographics", 11, "uq_acs_tract_geoid_year")
    _create_acs_table("acs_block_group_demographics", 12, "uq_acs_block_group_geoid_year")


def downgrade() -> None:
    op.drop_table("acs_block_group_demographics")
    op.drop_table("acs_tract_demographics")
