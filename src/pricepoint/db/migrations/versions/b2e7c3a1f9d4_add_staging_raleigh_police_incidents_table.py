"""add staging_raleigh_police_incidents table

Revision ID: b2e7c3a1f9d4
Revises: 40df3218b7aa
Create Date: 2026-02-05 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2e7c3a1f9d4"
down_revision: str | None = "40df3218b7aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_raleigh_police_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.String(), nullable=True),
        sa.Column("global_id", sa.String(), nullable=True),
        sa.Column("case_number", sa.String(), nullable=True),
        sa.Column("crime_category", sa.String(), nullable=True),
        sa.Column("crime_code", sa.String(), nullable=True),
        sa.Column("crime_description", sa.String(), nullable=True),
        sa.Column("crime_type", sa.String(), nullable=True),
        sa.Column("reported_block_address", sa.String(), nullable=True),
        sa.Column("city_of_incident", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("reported_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_year", sa.Integer(), nullable=True),
        sa.Column("reported_month", sa.Integer(), nullable=True),
        sa.Column("reported_day", sa.Integer(), nullable=True),
        sa.Column("reported_hour", sa.Integer(), nullable=True),
        sa.Column("reported_dayofwk", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("agency", sa.String(), nullable=True),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=True),
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
        op.f("ix_staging_raleigh_police_incidents_case_number"),
        "staging_raleigh_police_incidents",
        ["case_number"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_staging_raleigh_police_incidents_case_number"),
        table_name="staging_raleigh_police_incidents",
    )
    op.drop_table("staging_raleigh_police_incidents")
