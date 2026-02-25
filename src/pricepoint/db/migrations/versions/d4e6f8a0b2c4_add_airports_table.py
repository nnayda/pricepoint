"""Add airports table.

Revision ID: d4e6f8a0b2c4
Revises: c3d5e7f9a1b3
Create Date: 2026-02-25 00:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e6f8a0b2c4"
down_revision = "c3d5e7f9a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.UniqueConstraint("ident", name="uq_airports_ident"),
    )
    op.create_index("ix_airports_geom", "airports", ["geom"], postgresql_using="gist")
    op.create_index(op.f("ix_airports_ident"), "airports", ["ident"])
    op.create_index(op.f("ix_airports_name"), "airports", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_airports_name"), table_name="airports")
    op.drop_index(op.f("ix_airports_ident"), table_name="airports")
    op.drop_index("ix_airports_geom", table_name="airports", postgresql_using="gist")
    op.drop_table("airports")
