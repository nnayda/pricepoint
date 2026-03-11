"""Add acs_detailed_race table

Revision ID: t4u6v8w0x2y4
Revises: s3t5u7v9w1x3
Create Date: 2026-03-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t4u6v8w0x2y4"
down_revision: str | None = "s3t5u7v9w1x3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
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
        "ix_acs_detail_race_lookup",
        "acs_detailed_race",
        ["geography_level", "geoid", "acs_year"],
    )
    op.create_index(
        "ix_acs_detail_race_category",
        "acs_detailed_race",
        ["race_category"],
    )


def downgrade() -> None:
    op.drop_index("ix_acs_detail_race_category", table_name="acs_detailed_race")
    op.drop_index("ix_acs_detail_race_lookup", table_name="acs_detailed_race")
    op.drop_table("acs_detailed_race")
