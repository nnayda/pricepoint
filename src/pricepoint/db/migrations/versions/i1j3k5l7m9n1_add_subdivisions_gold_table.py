"""Add subdivisions gold table.

Revision ID: i1j3k5l7m9n1
Revises: j6k8l0m2n4p6
Create Date: 2026-02-27

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "i1j3k5l7m9n1"
down_revision = "j6k8l0m2n4p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("county_fips", "source_id", name="uq_subdivisions_county_source"),
    )
    op.create_index("ix_subdivisions_geom", "subdivisions", ["geom"], postgresql_using="gist")
    op.create_index("ix_subdivisions_name", "subdivisions", ["name"])
    op.create_index("ix_subdivisions_county_fips", "subdivisions", ["county_fips"])


def downgrade() -> None:
    op.drop_index("ix_subdivisions_county_fips", table_name="subdivisions")
    op.drop_index("ix_subdivisions_name", table_name="subdivisions")
    op.drop_index("ix_subdivisions_geom", table_name="subdivisions", postgresql_using="gist")
    op.drop_table("subdivisions")
