"""Replace greenspace tables with PAD-US schema.

Drop the staging_wake_open_space bronze table and recreate greenspaces
with the new PAD-US schema (source_id integer unique, gis_acres,
manager_type, designation_type, pub_access, gap_sts, state_name,
category, loaded_at).

Revision ID: z3a5b7c9d1e3
Revises: y2z4a6b8c0d2
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "z3a5b7c9d1e3"
down_revision = "y2z4a6b8c0d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old greenspaces gold table
    op.drop_table("greenspaces")

    # Drop staging_wake_open_space bronze table
    op.drop_table("staging_wake_open_space")

    # Create new greenspaces table with PAD-US schema
    op.create_table(
        "greenspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("gis_acres", sa.Float(), nullable=True),
        sa.Column("manager_type", sa.String(length=10), nullable=True),
        sa.Column("manager_name", sa.String(), nullable=True),
        sa.Column("designation_type", sa.String(length=20), nullable=True),
        sa.Column("pub_access", sa.String(length=2), nullable=True),
        sa.Column("gap_sts", sa.Integer(), nullable=True),
        sa.Column("state_name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
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
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_greenspaces_geom", "greenspaces", ["geom"], postgresql_using="gist")
    op.create_index(op.f("ix_greenspaces_name"), "greenspaces", ["name"])
    op.create_index(op.f("ix_greenspaces_source_id"), "greenspaces", ["source_id"])


def downgrade() -> None:
    # Drop new greenspaces table
    op.drop_index(op.f("ix_greenspaces_source_id"), table_name="greenspaces")
    op.drop_index(op.f("ix_greenspaces_name"), table_name="greenspaces")
    op.drop_index("ix_greenspaces_geom", table_name="greenspaces")
    op.drop_table("greenspaces")

    # Recreate old greenspaces gold table
    op.create_table(
        "greenspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
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
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_id", name="uq_greenspaces_source_source_id"),
    )
    op.create_index("ix_greenspaces_geom", "greenspaces", ["geom"], postgresql_using="gist")
    op.create_index(op.f("ix_greenspaces_name"), "greenspaces", ["name"])

    # Recreate staging_wake_open_space bronze table
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
    op.create_index(
        op.f("ix_staging_wake_open_space_objectid"),
        "staging_wake_open_space",
        ["objectid"],
    )
    op.create_index(
        op.f("ix_staging_wake_open_space_name"),
        "staging_wake_open_space",
        ["name"],
    )
