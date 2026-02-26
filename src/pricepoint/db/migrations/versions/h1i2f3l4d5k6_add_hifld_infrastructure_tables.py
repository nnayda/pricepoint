"""Add HIFLD infrastructure tables.

Revision ID: h1i2f3l4d5k6
Revises: v9w1x3y5z7a9
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "h1i2f3l4d5k6"
down_revision = "v9w1x3y5z7a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cell towers
    op.create_table(
        "hifld_cell_towers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("licensee", sa.String(), nullable=True),
        sa.Column("callsign", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("structure_type", sa.String(), nullable=True),
        sa.Column("height_ft", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hifld_cell_towers_objectid", "hifld_cell_towers", ["objectid"])
    op.create_index(
        "ix_hifld_cell_towers_geom",
        "hifld_cell_towers",
        ["geom"],
        postgresql_using="gist",
    )

    # Transmission lines
    op.create_table(
        "hifld_transmission_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("line_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("voltage", sa.Float(), nullable=True),
        sa.Column("volt_class", sa.String(), nullable=True),
        sa.Column("sub_1", sa.String(), nullable=True),
        sa.Column("sub_2", sa.String(), nullable=True),
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
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hifld_transmission_lines_objectid",
        "hifld_transmission_lines",
        ["objectid"],
    )
    op.create_index(
        "ix_hifld_transmission_lines_geom",
        "hifld_transmission_lines",
        ["geom"],
        postgresql_using="gist",
    )

    # Power plants
    op.create_table(
        "hifld_power_plants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("plant_code", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("utility_name", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("primary_source", sa.String(), nullable=True),
        sa.Column("install_mw", sa.Float(), nullable=True),
        sa.Column("total_mw", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hifld_power_plants_objectid", "hifld_power_plants", ["objectid"])
    op.create_index("ix_hifld_power_plants_name", "hifld_power_plants", ["name"])
    op.create_index(
        "ix_hifld_power_plants_geom",
        "hifld_power_plants",
        ["geom"],
        postgresql_using="gist",
    )

    # Natural gas pipelines
    op.create_table(
        "hifld_nat_gas_pipelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("pipe_type", sa.String(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
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
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hifld_nat_gas_pipelines_objectid",
        "hifld_nat_gas_pipelines",
        ["objectid"],
    )
    op.create_index(
        "ix_hifld_nat_gas_pipelines_geom",
        "hifld_nat_gas_pipelines",
        ["geom"],
        postgresql_using="gist",
    )

    # Petroleum pipelines
    op.create_table(
        "hifld_petroleum_pipelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("pipe_name", sa.String(), nullable=True),
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
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hifld_petroleum_pipelines_objectid",
        "hifld_petroleum_pipelines",
        ["objectid"],
    )
    op.create_index(
        "ix_hifld_petroleum_pipelines_geom",
        "hifld_petroleum_pipelines",
        ["geom"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_table("hifld_petroleum_pipelines")
    op.drop_table("hifld_nat_gas_pipelines")
    op.drop_table("hifld_power_plants")
    op.drop_table("hifld_transmission_lines")
    op.drop_table("hifld_cell_towers")
