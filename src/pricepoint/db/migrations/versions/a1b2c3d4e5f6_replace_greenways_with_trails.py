"""Replace greenway tables with USGS National Digital Trails.

Drop the staging greenway tables (wake, raleigh, cary) and the gold
greenways table. Create the new trails table with USGS schema.

Revision ID: a1b2c3d4e5f6
Revises: z3a5b7c9d1e3
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "z3a5b7c9d1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old greenway tables
    op.drop_table("greenways")
    op.drop_table("staging_wake_greenways")
    op.drop_table("staging_raleigh_greenways")
    op.drop_table("staging_cary_greenways")

    # Create new trails table
    op.create_table(
        "trails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("permanentidentifier", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("trail_type", sa.String(), nullable=True),
        sa.Column("length_miles", sa.Float(), nullable=True),
        sa.Column("maintainer", sa.String(), nullable=True),
        sa.Column("national_designation", sa.String(), nullable=True),
        sa.Column("hiker_pedestrian", sa.String(), nullable=True),
        sa.Column("bicycle", sa.String(), nullable=True),
        sa.Column("pack_saddle", sa.String(), nullable=True),
        sa.Column("atv", sa.String(), nullable=True),
        sa.Column("motorcycle", sa.String(), nullable=True),
        sa.Column("ohv_over_50_inches", sa.String(), nullable=True),
        sa.Column("snowshoe", sa.String(), nullable=True),
        sa.Column("cross_country_ski", sa.String(), nullable=True),
        sa.Column("dogsled", sa.String(), nullable=True),
        sa.Column("snowmobile", sa.String(), nullable=True),
        sa.Column("non_motorized_watercraft", sa.String(), nullable=True),
        sa.Column("motorized_watercraft", sa.String(), nullable=True),
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
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("permanentidentifier"),
    )
    op.create_index("ix_trails_permanentidentifier", "trails", ["permanentidentifier"])
    op.create_index("ix_trails_name", "trails", ["name"])
    op.create_index("ix_trails_geom", "trails", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("trails")

    # Recreate old tables (simplified — does not restore data)
    op.create_table(
        "staging_wake_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("trail_name", sa.String(), nullable=True),
        sa.Column("corridor_name", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("trail_status", sa.String(), nullable=True),
        sa.Column("trail_surface", sa.String(), nullable=True),
        sa.Column("trail_class", sa.String(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("open_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_access", sa.String(), nullable=True),
        sa.Column("accessibility_status", sa.String(), nullable=True),
        sa.Column("trail_condition", sa.String(), nullable=True),
        sa.Column("slope", sa.String(), nullable=True),
        sa.Column("subsegment_name", sa.String(), nullable=True),
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
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "staging_raleigh_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("trail_name", sa.String(), nullable=True),
        sa.Column("greenway_type", sa.String(), nullable=True),
        sa.Column("location_desc", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("map_miles", sa.Float(), nullable=True),
        sa.Column("width_ft", sa.Float(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("ada", sa.String(), nullable=True),
        sa.Column("gw_status", sa.String(), nullable=True),
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
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "staging_cary_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("segment", sa.String(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("trail_type", sa.String(), nullable=True),
        sa.Column("surface_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("install_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_to_public", sa.String(), nullable=True),
        sa.Column("project_name", sa.String(), nullable=True),
        sa.Column("project_number", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("loop_trail", sa.String(), nullable=True),
        sa.Column("loop_name", sa.String(), nullable=True),
        sa.Column("official_cary_greenway_miles", sa.Float(), nullable=True),
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
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

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
        sa.UniqueConstraint("source", "source_id", name="uq_greenways_source_source_id"),
    )
    op.create_index("ix_greenways_geom", "greenways", ["geom"], postgresql_using="gist")
