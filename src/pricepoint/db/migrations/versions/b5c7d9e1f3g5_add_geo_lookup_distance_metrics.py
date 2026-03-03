"""Add distance and school metrics to property_geo_lookups.

Revision ID: b5c7d9e1f3g5
Revises: a4b6c8d0e2f4
Create Date: 2026-03-03

"""

import sqlalchemy as sa
from alembic import op

revision = "b5c7d9e1f3g5"
down_revision = "a4b6c8d0e2f4"
branch_labels = None
depends_on = None

_TABLE = "property_geo_lookups"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_school_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_elementary_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_middle_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_high_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_park_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_greenway_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("dist_nearest_hospital_m", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("avg_school_rating", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("avg_school_drive", sa.Float(), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "in_critical_risk_zone",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "in_critical_risk_zone")
    op.drop_column(_TABLE, "avg_school_drive")
    op.drop_column(_TABLE, "avg_school_rating")
    op.drop_column(_TABLE, "dist_nearest_hospital_m")
    op.drop_column(_TABLE, "dist_nearest_greenway_m")
    op.drop_column(_TABLE, "dist_nearest_park_m")
    op.drop_column(_TABLE, "dist_nearest_high_m")
    op.drop_column(_TABLE, "dist_nearest_middle_m")
    op.drop_column(_TABLE, "dist_nearest_elementary_m")
    op.drop_column(_TABLE, "dist_nearest_school_m")
