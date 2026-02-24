"""Greenspace bronze tables: drop parks, rename greenways, add open space.

Revision ID: s6u8w0y2b4d6
Revises: r5t7v9x1z3a5
Create Date: 2026-02-24

"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "s6u8w0y2b4d6"
down_revision = "r5t7v9x1z3a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop park tables
    op.drop_table("cary_parks")
    op.drop_table("raleigh_parks")
    op.drop_table("wake_parks")

    # Rename greenway tables to staging prefix
    op.rename_table("wake_greenways", "staging_wake_greenways")
    op.rename_table("raleigh_greenways", "staging_raleigh_greenways")
    op.rename_table("cary_greenways", "staging_cary_greenways")

    # Create staging_wake_open_space
    op.create_table(
        "staging_wake_open_space",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("manager", sa.String(), nullable=True),
        sa.Column("comments", sa.String(), nullable=True),
        sa.Column("bldgcode", sa.String(), nullable=True),
        sa.Column("corridor", sa.String(), nullable=True),
        sa.Column("os_number", sa.String(), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_edited_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staging_wake_open_space_objectid",
        "staging_wake_open_space",
        ["objectid"],
    )
    op.create_index(
        "ix_staging_wake_open_space_name",
        "staging_wake_open_space",
        ["name"],
    )


def downgrade() -> None:
    # Drop staging_wake_open_space
    op.drop_index("ix_staging_wake_open_space_name", table_name="staging_wake_open_space")
    op.drop_index("ix_staging_wake_open_space_objectid", table_name="staging_wake_open_space")
    op.drop_table("staging_wake_open_space")

    # Rename greenway tables back
    op.rename_table("staging_cary_greenways", "cary_greenways")
    op.rename_table("staging_raleigh_greenways", "raleigh_greenways")
    op.rename_table("staging_wake_greenways", "wake_greenways")

    # Recreate park tables
    op.create_table(
        "wake_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("park_type", sa.String(), nullable=True),
        sa.Column("manager", sa.String(), nullable=True),
        sa.Column("comments", sa.String(), nullable=True),
        sa.Column("corridor", sa.String(), nullable=True),
        sa.Column("os_number", sa.String(), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_edited_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_parks_objectid", "wake_parks", ["objectid"])
    op.create_index("ix_wake_parks_name", "wake_parks", ["name"])

    op.create_table(
        "raleigh_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("park_type", sa.String(), nullable=True),
        sa.Column("developed", sa.String(), nullable=True),
        sa.Column("map_acres", sa.Float(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("park_id", sa.String(), nullable=True),
        sa.Column("initial_acquisition_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raleigh_parks_objectid", "raleigh_parks", ["objectid"])
    op.create_index("ix_raleigh_parks_name", "raleigh_parks", ["name"])

    op.create_table(
        "cary_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("facility_id", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("park_area", sa.Float(), nullable=True),
        sa.Column("park_url", sa.String(), nullable=True),
        sa.Column("num_parking", sa.Integer(), nullable=True),
        sa.Column("restroom", sa.String(), nullable=True),
        sa.Column("ada_compliant", sa.String(), nullable=True),
        sa.Column("camping", sa.String(), nullable=True),
        sa.Column("swimming", sa.String(), nullable=True),
        sa.Column("hiking", sa.String(), nullable=True),
        sa.Column("fishing", sa.String(), nullable=True),
        sa.Column("picnic", sa.String(), nullable=True),
        sa.Column("boating", sa.String(), nullable=True),
        sa.Column("road_cycle", sa.String(), nullable=True),
        sa.Column("mtb_cycle", sa.String(), nullable=True),
        sa.Column("playground", sa.String(), nullable=True),
        sa.Column("golf", sa.String(), nullable=True),
        sa.Column("soccer", sa.String(), nullable=True),
        sa.Column("baseball", sa.String(), nullable=True),
        sa.Column("basketball", sa.String(), nullable=True),
        sa.Column("skatepark", sa.String(), nullable=True),
        sa.Column("tennis_court", sa.String(), nullable=True),
        sa.Column("volleyball", sa.String(), nullable=True),
        sa.Column("fitness_trail", sa.String(), nullable=True),
        sa.Column("nature_trail", sa.String(), nullable=True),
        sa.Column("trailhead", sa.String(), nullable=True),
        sa.Column("open_space", sa.String(), nullable=True),
        sa.Column("lake", sa.String(), nullable=True),
        sa.Column("amphitheater", sa.String(), nullable=True),
        sa.Column("dog_park", sa.String(), nullable=True),
        sa.Column("disc_golf", sa.String(), nullable=True),
        sa.Column("climbing_rocks", sa.String(), nullable=True),
        sa.Column("climbing_ropes", sa.String(), nullable=True),
        sa.Column("batting_cages", sa.String(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cary_parks_objectid", "cary_parks", ["objectid"])
    op.create_index("ix_cary_parks_name", "cary_parks", ["name"])
