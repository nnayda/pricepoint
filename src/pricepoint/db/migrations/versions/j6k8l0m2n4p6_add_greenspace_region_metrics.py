"""Add greenspace_region_metrics table.

Revision ID: j6k8l0m2n4p6
Revises: h1i2f3l4d5k6
Create Date: 2026-02-27

"""

import sqlalchemy as sa
from alembic import op

revision = "j6k8l0m2n4p6"
down_revision = "h1i2f3l4d5k6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "greenspace_region_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("geo_level", sa.String(length=25), nullable=False),
        sa.Column("geoid", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("park_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_park_acres", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_trail_miles", sa.Float(), nullable=False, server_default="0"),
        sa.Column("greenspace_area_sqm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("region_land_area_sqm", sa.Float(), nullable=False, server_default="0"),
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
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("geo_level", "geoid", name="uq_greenspace_region_level_geoid"),
    )
    op.create_index(
        "ix_greenspace_region_metrics_geo_level",
        "greenspace_region_metrics",
        ["geo_level"],
    )
    op.create_index(
        "ix_greenspace_region_metrics_geoid",
        "greenspace_region_metrics",
        ["geoid"],
    )


def downgrade() -> None:
    op.drop_index("ix_greenspace_region_metrics_geoid", table_name="greenspace_region_metrics")
    op.drop_index("ix_greenspace_region_metrics_geo_level", table_name="greenspace_region_metrics")
    op.drop_table("greenspace_region_metrics")
