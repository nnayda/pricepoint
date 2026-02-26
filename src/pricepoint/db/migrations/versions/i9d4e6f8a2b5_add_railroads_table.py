"""Add railroads table for HIFLD rail network lines.

Revision ID: i9d4e6f8a2b5
Revises: h8c3d5e7f9a1
Create Date: 2026-02-26 00:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9d4e6f8a2b5"
down_revision: str | None = "h8c3d5e7f9a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "railroads",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("fraarcid", sa.Integer(), nullable=True),
        sa.Column("rrowner1", sa.String(), nullable=True),
        sa.Column("rrowner2", sa.String(), nullable=True),
        sa.Column("rrowner3", sa.String(), nullable=True),
        sa.Column("stateab", sa.String(length=2), nullable=True),
        sa.Column("cntyfips", sa.String(length=5), nullable=True),
        sa.Column("subdivision", sa.String(), nullable=True),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("passngr", sa.String(), nullable=True),
        sa.Column("tracks", sa.Integer(), nullable=True),
        sa.Column("miles", sa.Float(), nullable=True),
        sa.Column("net", sa.String(), nullable=True),
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
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint("fraarcid"),
    )
    op.create_index("ix_railroads_geom", "railroads", ["geom"], postgresql_using="gist")
    op.create_index("ix_railroads_fraarcid", "railroads", ["fraarcid"])


def downgrade() -> None:
    op.drop_index("ix_railroads_fraarcid", table_name="railroads")
    op.drop_index("ix_railroads_geom", table_name="railroads", postgresql_using="gist")
    op.drop_table("railroads")
