"""Add noises table.

Revision ID: e5f7a1b3c5d7
Revises: d4e6f8a0b2c4
Create Date: 2026-02-25 00:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f7a1b3c5d7"
down_revision = "d4e6f8a0b2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.create_index("ix_noises_geom", "noises", ["geom"], postgresql_using="gist")
    op.create_index("ix_noises_noise_min_db", "noises", ["noise_min_db"])


def downgrade() -> None:
    op.drop_index("ix_noises_noise_min_db", table_name="noises")
    op.drop_index("ix_noises_geom", table_name="noises", postgresql_using="gist")
    op.drop_table("noises")
