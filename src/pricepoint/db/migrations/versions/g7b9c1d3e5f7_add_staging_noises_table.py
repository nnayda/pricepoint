"""Add staging_noises table.

Revision ID: g7b9c1d3e5f7
Revises: f6a8b2c4d6e8
Create Date: 2026-02-26 00:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "g7b9c1d3e5f7"
down_revision = "f6a8b2c4d6e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("staging_noises")
