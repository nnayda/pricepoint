"""Alter police_incidents table for gold layer.

Revision ID: u5v7w9x1y3z5
Revises: t4u6v8w0x2y4
Create Date: 2026-03-11 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "u5v7w9x1y3z5"
down_revision = "t4u6v8w0x2y4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old columns
    op.drop_column("police_incidents", "incident_type")
    op.drop_column("police_incidents", "occurred_at")

    # Add new columns
    op.add_column("police_incidents", sa.Column("crime_code", sa.String(), nullable=True))
    op.add_column("police_incidents", sa.Column("crime_group", sa.String(), nullable=True))
    op.add_column("police_incidents", sa.Column("crime_category", sa.String(), nullable=True))
    op.add_column("police_incidents", sa.Column("crime_description", sa.String(), nullable=True))
    op.add_column("police_incidents", sa.Column("address", sa.String(), nullable=True))
    op.add_column("police_incidents", sa.Column("date_of_incident", sa.Date(), nullable=True))
    op.add_column("police_incidents", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("police_incidents", sa.Column("longitude", sa.Float(), nullable=True))

    # Add indexes
    op.create_index(
        "ix_police_incidents_location",
        "police_incidents",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_police_incidents_crime_category",
        "police_incidents",
        ["crime_category"],
    )
    op.create_index(
        "ix_police_incidents_date_of_incident",
        "police_incidents",
        ["date_of_incident"],
    )


def downgrade() -> None:
    op.drop_index("ix_police_incidents_date_of_incident", table_name="police_incidents")
    op.drop_index("ix_police_incidents_crime_category", table_name="police_incidents")
    op.drop_index("ix_police_incidents_location", table_name="police_incidents")

    op.drop_column("police_incidents", "longitude")
    op.drop_column("police_incidents", "latitude")
    op.drop_column("police_incidents", "date_of_incident")
    op.drop_column("police_incidents", "address")
    op.drop_column("police_incidents", "crime_description")
    op.drop_column("police_incidents", "crime_category")
    op.drop_column("police_incidents", "crime_group")
    op.drop_column("police_incidents", "crime_code")

    op.add_column(
        "police_incidents",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "police_incidents",
        sa.Column("incident_type", sa.String(), nullable=True),
    )
