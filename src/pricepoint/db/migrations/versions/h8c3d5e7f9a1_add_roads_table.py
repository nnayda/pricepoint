"""Add roads table.

Revision ID: h8c3d5e7f9a1
Revises: g7b9c1d3e5f7
Create Date: 2026-02-26 00:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "h8c3d5e7f9a1"
down_revision = "g7b9c1d3e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.UniqueConstraint("linearid"),
    )
    op.create_index("ix_roads_geom", "roads", ["geom"], postgresql_using="gist")
    op.create_index(op.f("ix_roads_linearid"), "roads", ["linearid"])


def downgrade() -> None:
    op.drop_index(op.f("ix_roads_linearid"), table_name="roads")
    op.drop_index("ix_roads_geom", table_name="roads", postgresql_using="gist")
    op.drop_table("roads")
