"""Replace property_details with redfin_listings

Revision ID: b8d4f2a7c3e1
Revises: a7b3c5d9e1f0
Create Date: 2026-02-13 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d4f2a7c3e1"
down_revision: str | None = "a7b3c5d9e1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop old tables (property_details stored data will be re-transformed)
    op.drop_table("property_schools")
    op.drop_table("property_valuations")
    op.drop_index("ix_property_details_address", table_name="property_details")
    op.drop_table("property_details")

    # Create redfin_listings table
    op.create_table(
        "redfin_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Location
        sa.Column("street_address", sa.String(), nullable=False),
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
        sa.Column("description", sa.Text(), nullable=True),
        # Climate
        sa.Column("flood_factor", sa.String(), nullable=True),
        sa.Column("fire_factor", sa.String(), nullable=True),
        sa.Column("flood_score", sa.Integer(), nullable=True),
        sa.Column("fire_score", sa.Integer(), nullable=True),
        # Parking
        sa.Column("has_garage", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("num_garage_spaces", sa.Integer(), nullable=True),
        sa.Column("parking_type", sa.String(), nullable=True),
        sa.Column("garage_entry", sa.String(), nullable=True),
        sa.Column("driveway_surface", sa.String(), nullable=True),
        sa.Column("has_workshop", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_circular_driveway", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_ev_charging", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("num_parking_spaces", sa.Integer(), nullable=True),
        # Fireplace
        sa.Column("has_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_outdoor_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_primary_fireplace", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_architectural_fireplace",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("fireplace_fuel_source", sa.String(), nullable=True),
        sa.Column("num_fireplaces", sa.Integer(), nullable=True),
        # Appliances / energy
        sa.Column("water_heater_energy_source", sa.String(), nullable=True),
        sa.Column("cooktop_energy_source", sa.String(), nullable=True),
        sa.Column("oven_energy_source", sa.String(), nullable=True),
        sa.Column("has_drink_fridge", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_stainless_appliances",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("appliances_included_count", sa.Integer(), nullable=True),
        # Windows
        sa.Column(
            "has_efficient_windows", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_skylights", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_bay_window", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        # Laundry
        sa.Column("laundry_location", sa.String(), nullable=True),
        sa.Column("has_laundry_room", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_utility_sink", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        # Interior features
        sa.Column("countertop_material", sa.String(), nullable=True),
        sa.Column(
            "is_primary_downstairs", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_guest_suite", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_butler_pantry", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_walkin_closets", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_tall_ceilings", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_luxury_ceilings", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_sauna", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_bar", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_second_primary", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_room_over_garage", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column(
            "has_open_floorplan", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        # Flooring
        sa.Column("is_carpet_free", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_premium_stone", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_hardwood", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_crawl_space", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        # Exterior / structure
        sa.Column("facade_type", sa.String(), nullable=True),
        sa.Column("building_area", sa.Float(), nullable=True),
        sa.Column("above_grade_finished_area", sa.Float(), nullable=True),
        sa.Column("below_grade_finished_area", sa.Float(), nullable=True),
        sa.Column("num_stories", sa.Float(), nullable=True),
        sa.Column("lot_size", sa.Float(), nullable=True),
        sa.Column("is_waterfront", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("buyer_financing", sa.String(), nullable=True),
        # Utilities
        sa.Column("is_septic", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_well_water", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("no_heating", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("no_cooling", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        # HOA / community
        sa.Column("has_hoa", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("association_fee", sa.Float(), nullable=True),
        sa.Column("hoa_name", sa.String(), nullable=True),
        # Porch / outdoor
        sa.Column(
            "has_enclosed_porch", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_front_porch", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_fenced_yard", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_outdoor_kitchen", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_sport_court", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("has_private_pool", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_community_pool", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_clubhouse", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column(
            "has_exterior_storage", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.Column("has_garden", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        # Core stats
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("num_beds", sa.Integer(), nullable=True),
        sa.Column("num_baths", sa.Float(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("price_per_sqft", sa.Float(), nullable=True),
        # Agents
        sa.Column("listing_agent", sa.String(), nullable=True),
        sa.Column("listing_brokerage", sa.String(), nullable=True),
        sa.Column("buying_agent", sa.String(), nullable=True),
        sa.Column("buying_brokerage", sa.String(), nullable=True),
        # Identifiers
        sa.Column("apn", sa.String(), nullable=True),
        sa.Column("contract_date", sa.DateTime(), nullable=True),
        # Raw data for UI
        sa.Column("property_details", sa.JSON(), nullable=True),
        # Photos and source
        sa.Column("property_photos", sa.JSON(), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        # Change detection
        sa.Column("staging_hash", sa.String(64), nullable=True),
        # Metadata
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_redfin_listings_street_address", "redfin_listings", ["street_address"])
    op.create_index(
        "uq_redfin_listings_address",
        "redfin_listings",
        ["street_address", "city", "state", "zip_code"],
        unique=True,
    )

    # Create sale_history table
    op.create_table(
        "sale_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_history_property_id", "sale_history", ["property_id"])

    # Create tax_history table
    op.create_table(
        "tax_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("property_tax", sa.Float(), nullable=True),
        sa.Column("assessment_value_land", sa.Float(), nullable=True),
        sa.Column("assessment_value_additions", sa.Float(), nullable=True),
        sa.Column("assessment_value", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_history_property_id", "tax_history", ["property_id"])

    # Recreate property_valuations and property_schools (FK semantics now point to redfin_listings)
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
    op.drop_index("ix_tax_history_property_id", table_name="tax_history")
    op.drop_table("tax_history")
    op.drop_index("ix_sale_history_property_id", table_name="sale_history")
    op.drop_table("sale_history")
    op.drop_index("uq_redfin_listings_address", table_name="redfin_listings")
    op.drop_index("ix_redfin_listings_street_address", table_name="redfin_listings")
    op.drop_table("redfin_listings")

    # Recreate old property_details table (structure from f4c8d2e6a1b3)
    op.create_table(
        "property_details",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.Column("listing_status", sa.String(), nullable=True),
        sa.Column("sold_date", sa.DateTime(), nullable=True),
        sa.Column("sold_price", sa.Float(), nullable=True),
        sa.Column("listing_price", sa.Float(), nullable=True),
        sa.Column("price_per_sqft", sa.Float(), nullable=True),
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Float(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("lot_size_sqft", sa.Float(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("stories", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flooring", sa.JSON(), nullable=True),
        sa.Column("appliances", sa.JSON(), nullable=True),
        sa.Column("heating", sa.String(), nullable=True),
        sa.Column("cooling", sa.String(), nullable=True),
        sa.Column("fireplace", sa.String(), nullable=True),
        sa.Column("basement", sa.String(), nullable=True),
        sa.Column("roof", sa.String(), nullable=True),
        sa.Column("siding", sa.String(), nullable=True),
        sa.Column("foundation", sa.String(), nullable=True),
        sa.Column("parking", sa.String(), nullable=True),
        sa.Column("garage_spaces", sa.Integer(), nullable=True),
        sa.Column("pool", sa.String(), nullable=True),
        sa.Column("fence", sa.String(), nullable=True),
        sa.Column("hoa_monthly", sa.Float(), nullable=True),
        sa.Column("tax_annual", sa.Float(), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("assessed_value", sa.Float(), nullable=True),
        sa.Column("listing_agent", sa.String(), nullable=True),
        sa.Column("listing_brokerage", sa.String(), nullable=True),
        sa.Column("buying_agent", sa.String(), nullable=True),
        sa.Column("buying_brokerage", sa.String(), nullable=True),
        sa.Column("flood_risk", sa.String(), nullable=True),
        sa.Column("flood_score", sa.Integer(), nullable=True),
        sa.Column("fire_risk", sa.String(), nullable=True),
        sa.Column("fire_score", sa.Integer(), nullable=True),
        sa.Column("sale_history", sa.JSON(), nullable=True),
        sa.Column("tax_history", sa.JSON(), nullable=True),
        sa.Column("photo_s3_paths", sa.JSON(), nullable=True),
        sa.Column("staging_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_details_address", "property_details", ["address"], unique=True)

    # Recreate property_valuations and property_schools
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
