"""add staging_morrisville_police_incidents table

Revision ID: c4f8d2b3e5a6
Revises: b2e7c3a1f9d4
Create Date: 2026-02-05 14:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f8d2b3e5a6"
down_revision: str | None = "b2e7c3a1f9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_morrisville_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("inci_id", sa.String(), nullable=True),
        sa.Column("offense", sa.String(), nullable=True),
        sa.Column("date_rept", sa.String(), nullable=True),
        sa.Column("date_occu", sa.String(), nullable=True),
        sa.Column("dow1", sa.String(), nullable=True),
        sa.Column("monthstamp", sa.String(), nullable=True),
        sa.Column("yearstamp", sa.String(), nullable=True),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip", sa.String(), nullable=True),
        sa.Column("neighborhd", sa.String(), nullable=True),
        sa.Column("subdivisn", sa.String(), nullable=True),
        sa.Column("tract", sa.String(), nullable=True),
        sa.Column("zone", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("asst_offcr", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT"
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
    op.create_index(
        op.f("ix_staging_morrisville_police_incidents_inci_id"),
        "staging_morrisville_police_incidents",
        ["inci_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_staging_morrisville_police_incidents_inci_id"),
        table_name="staging_morrisville_police_incidents",
    )
    op.drop_table("staging_morrisville_police_incidents")
