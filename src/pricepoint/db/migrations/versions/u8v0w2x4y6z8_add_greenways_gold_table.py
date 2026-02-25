"""Add greenways gold table.

Revision ID: u8v0w2x4y6z8
Revises: t7u9v1w3x5y7
Create Date: 2026-02-24

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "u8v0w2x4y6z8"
down_revision = "t7u9v1w3x5y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("surface_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
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
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_greenways_name", "greenways", ["name"])
    op.create_index(
        "ix_greenways_source_source_id", "greenways", ["source", "source_id"]
    )
    op.create_index(
        "ix_greenways_geom", "greenways", ["geom"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("ix_greenways_geom", table_name="greenways", postgresql_using="gist")
    op.drop_index("ix_greenways_source_source_id", table_name="greenways")
    op.drop_index("ix_greenways_name", table_name="greenways")
    op.drop_table("greenways")
