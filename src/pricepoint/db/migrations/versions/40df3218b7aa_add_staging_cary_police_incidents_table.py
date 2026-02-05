"""add staging_cary_police_incidents table

Revision ID: 40df3218b7aa
Revises:
Create Date: 2026-02-05 02:05:43.845962

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40df3218b7aa"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_cary_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_id", sa.String(), nullable=True),
        sa.Column("incident_number", sa.String(), nullable=True),
        sa.Column("crime_category", sa.String(), nullable=True),
        sa.Column("crime_type", sa.String(), nullable=True),
        sa.Column("ucr", sa.String(), nullable=True),
        sa.Column("map_reference", sa.String(), nullable=True),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("from_time", sa.String(), nullable=True),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("to_time", sa.String(), nullable=True),
        sa.Column("crimeday", sa.String(), nullable=True),
        sa.Column("geocode", sa.String(), nullable=True),
        sa.Column("location_category", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("beat_number", sa.String(), nullable=True),
        sa.Column("neighborhd_id", sa.String(), nullable=True),
        sa.Column("apartment_complex", sa.String(), nullable=True),
        sa.Column("residential_subdivision", sa.String(), nullable=True),
        sa.Column("subdivisn_id", sa.String(), nullable=True),
        sa.Column("activity_date", sa.String(), nullable=True),
        sa.Column("phxrecordstatus", sa.String(), nullable=True),
        sa.Column("phxcommunity", sa.String(), nullable=True),
        sa.Column("phxstatus", sa.String(), nullable=True),
        sa.Column("record", sa.String(), nullable=True),
        sa.Column("offensecategory", sa.String(), nullable=True),
        sa.Column("violentproperty", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column("domestic", sa.String(), nullable=True),
        sa.Column("total_incidents", sa.String(), nullable=True),
        sa.Column("year", sa.String(), nullable=True),
        sa.Column("older_than_five_years_from_now", sa.String(), nullable=True),
        sa.Column("chrgcnt", sa.String(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
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
        op.f("ix_staging_cary_police_incidents_api_id"),
        "staging_cary_police_incidents",
        ["api_id"],
    )
    op.create_index(
        op.f("ix_staging_cary_police_incidents_incident_number"),
        "staging_cary_police_incidents",
        ["incident_number"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_staging_cary_police_incidents_incident_number"),
        table_name="staging_cary_police_incidents",
    )
    op.drop_index(
        op.f("ix_staging_cary_police_incidents_api_id"),
        table_name="staging_cary_police_incidents",
    )
    op.drop_table("staging_cary_police_incidents")
