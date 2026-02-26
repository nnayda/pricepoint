"""Add greenspaces gold table.

Revision ID: v9w1x3y5z7a9
Revises: u8v0w2x4y6z8
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "v9w1x3y5z7a9"
down_revision = "u8v0w2x4y6z8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "greenspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
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
    )
    op.create_index("ix_greenspaces_name", "greenspaces", ["name"])
    op.create_index("ix_greenspaces_source_source_id", "greenspaces", ["source", "source_id"])
    op.create_index("ix_greenspaces_geom", "greenspaces", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_greenspaces_geom", table_name="greenspaces", postgresql_using="gist")
    op.drop_index("ix_greenspaces_source_source_id", table_name="greenspaces")
    op.drop_index("ix_greenspaces_name", table_name="greenspaces")
    op.drop_table("greenspaces")
