"""Add property production tables

Revision ID: f4c8d2e6a1b3
Revises: e3b7f1c9d4a6
Create Date: 2026-02-10 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4c8d2e6a1b3"
down_revision: str | None = "e3b7f1c9d4a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create schools table
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("grades", sa.String(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create property_details table
    op.create_table(
        "property_details",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Location
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        # Listing
        sa.Column("listing_status", sa.String(), nullable=True),
        sa.Column("sold_date", sa.DateTime(), nullable=True),
        sa.Column("sold_price", sa.Float(), nullable=True),
        sa.Column("listing_price", sa.Float(), nullable=True),
        sa.Column("price_per_sqft", sa.Float(), nullable=True),
        # Stats
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Float(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("lot_size_sqft", sa.Float(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("stories", sa.Integer(), nullable=True),
        # Description
        sa.Column("description", sa.Text(), nullable=True),
        # Interior
        sa.Column("flooring", sa.JSON(), nullable=True),
        sa.Column("appliances", sa.JSON(), nullable=True),
        sa.Column("heating", sa.String(), nullable=True),
        sa.Column("cooling", sa.String(), nullable=True),
        sa.Column("fireplace", sa.String(), nullable=True),
        sa.Column("basement", sa.String(), nullable=True),
        # Exterior
        sa.Column("roof", sa.String(), nullable=True),
        sa.Column("siding", sa.String(), nullable=True),
        sa.Column("foundation", sa.String(), nullable=True),
        sa.Column("parking", sa.String(), nullable=True),
        sa.Column("garage_spaces", sa.Integer(), nullable=True),
        sa.Column("pool", sa.String(), nullable=True),
        sa.Column("fence", sa.String(), nullable=True),
        # Financial
        sa.Column("hoa_monthly", sa.Float(), nullable=True),
        sa.Column("tax_annual", sa.Float(), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("assessed_value", sa.Float(), nullable=True),
        # Agents
        sa.Column("listing_agent", sa.String(), nullable=True),
        sa.Column("listing_brokerage", sa.String(), nullable=True),
        sa.Column("buying_agent", sa.String(), nullable=True),
        sa.Column("buying_brokerage", sa.String(), nullable=True),
        # Climate
        sa.Column("flood_risk", sa.String(), nullable=True),
        sa.Column("flood_score", sa.Integer(), nullable=True),
        sa.Column("fire_risk", sa.String(), nullable=True),
        sa.Column("fire_score", sa.Integer(), nullable=True),
        # History
        sa.Column("sale_history", sa.JSON(), nullable=True),
        sa.Column("tax_history", sa.JSON(), nullable=True),
        # Photos
        sa.Column("photo_s3_paths", sa.JSON(), nullable=True),
        # Change detection
        sa.Column("staging_hash", sa.String(64), nullable=True),
        # Metadata
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_details_address", "property_details", ["address"], unique=True)
    # Note: GeoAlchemy2 auto-creates idx_property_details_location GiST index

    # Create property_valuations table
    op.create_table(
        "property_valuations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("confidence_low", sa.Float(), nullable=True),
        sa.Column("confidence_high", sa.Float(), nullable=True),
        sa.Column(
            "estimated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_valuations_property_id", "property_valuations", ["property_id"])
    op.create_index(
        "idx_property_valuations_property_source",
        "property_valuations",
        ["property_id", "source"],
    )

    # Create property_schools table
    op.create_table(
        "property_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("distance_miles", sa.Float(), nullable=True),
        sa.Column("drive_minutes", sa.Integer(), nullable=True),
        sa.Column("walk_minutes", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_schools_property_id", "property_schools", ["property_id"])
    op.create_index("ix_property_schools_school_id", "property_schools", ["school_id"])
    op.create_index(
        "uq_property_school",
        "property_schools",
        ["property_id", "school_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("property_schools")
    op.drop_table("property_valuations")
    op.drop_index("ix_property_details_address", table_name="property_details")
    op.drop_table("property_details")
    op.drop_table("schools")
