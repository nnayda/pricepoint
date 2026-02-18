"""Add wake subdivisions table

Revision ID: g5d2e7f1a8c3
Revises: d1f6a4b8c3e7
Create Date: 2026-02-18 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g5d2e7f1a8c3"
down_revision: str | None = "d1f6a4b8c3e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wake_subdivisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=40), nullable=True),
        sa.Column("snumber", sa.String(length=10), nullable=True),
        sa.Column("access_rd", sa.String(length=30), nullable=True),
        sa.Column("jurisdiction", sa.String(length=25), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("lots", sa.Integer(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("mapclass", sa.Integer(), nullable=True),
        sa.Column("iscluster", sa.String(length=5), nullable=True),
        sa.Column("approvdate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appldate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_edited_date", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_wake_subdivisions_objectid", "wake_subdivisions", ["objectid"])
    op.create_index("ix_wake_subdivisions_snumber", "wake_subdivisions", ["snumber"])


def downgrade() -> None:
    op.drop_index("ix_wake_subdivisions_snumber", table_name="wake_subdivisions")
    op.drop_index("ix_wake_subdivisions_objectid", table_name="wake_subdivisions")
    op.drop_table("wake_subdivisions")
