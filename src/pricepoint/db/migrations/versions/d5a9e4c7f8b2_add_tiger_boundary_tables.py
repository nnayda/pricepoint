"""add tiger boundary tables

Revision ID: d5a9e4c7f8b2
Revises: c4f8d2b3e5a6
Create Date: 2026-02-06 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a9e4c7f8b2"
down_revision: str | None = "c4f8d2b3e5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- tiger_census_blocks ---------------------------------------------------
    op.create_table(
        "tiger_census_blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp20", sa.String(length=2), nullable=True),
        sa.Column("countyfp20", sa.String(length=3), nullable=True),
        sa.Column("tractce20", sa.String(length=6), nullable=True),
        sa.Column("blockce20", sa.String(length=4), nullable=True),
        sa.Column("geoid20", sa.String(length=15), nullable=True),
        sa.Column("name20", sa.String(), nullable=True),
        sa.Column("aland20", sa.BigInteger(), nullable=True),
        sa.Column("awater20", sa.BigInteger(), nullable=True),
        sa.Column("intptlat20", sa.String(length=11), nullable=True),
        sa.Column("intptlon20", sa.String(length=12), nullable=True),
        sa.Column("funcstat20", sa.String(length=1), nullable=True),
        sa.Column("mtfcc20", sa.String(length=5), nullable=True),
        sa.Column("ur20", sa.String(length=1), nullable=True),
        sa.Column("uace20", sa.String(length=5), nullable=True),
        sa.Column("uatype20", sa.String(length=1), nullable=True),
        sa.Column("housing20", sa.Integer(), nullable=True),
        sa.Column("pop20", sa.Integer(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_census_blocks_geoid20"),
        "tiger_census_blocks",
        ["geoid20"],
    )
    op.create_index(
        "ix_tiger_census_blocks_geom",
        "tiger_census_blocks",
        ["geom"],
        postgresql_using="gist",
    )

    # -- tiger_block_groups ----------------------------------------------------
    op.create_table(
        "tiger_block_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("tractce", sa.String(length=6), nullable=True),
        sa.Column("blkgrpce", sa.String(length=1), nullable=True),
        sa.Column("geoid", sa.String(length=12), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_block_groups_geoid"),
        "tiger_block_groups",
        ["geoid"],
    )
    op.create_index(
        "ix_tiger_block_groups_geom",
        "tiger_block_groups",
        ["geom"],
        postgresql_using="gist",
    )

    # -- tiger_tracts ----------------------------------------------------------
    op.create_table(
        "tiger_tracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("tractce", sa.String(length=6), nullable=True),
        sa.Column("geoid", sa.String(length=11), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_tracts_geoid"),
        "tiger_tracts",
        ["geoid"],
    )
    op.create_index(
        "ix_tiger_tracts_geom",
        "tiger_tracts",
        ["geom"],
        postgresql_using="gist",
    )

    # -- tiger_school_districts ------------------------------------------------
    op.create_table(
        "tiger_school_districts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("district_type", sa.String(length=10), nullable=True),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("geoid", sa.String(length=7), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("lograde", sa.String(length=2), nullable=True),
        sa.Column("higrade", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("sdtyp", sa.String(length=1), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_school_districts_district_type"),
        "tiger_school_districts",
        ["district_type"],
    )
    op.create_index(
        op.f("ix_tiger_school_districts_geoid"),
        "tiger_school_districts",
        ["geoid"],
    )
    op.create_index(
        "ix_tiger_school_districts_geom",
        "tiger_school_districts",
        ["geom"],
        postgresql_using="gist",
    )

    # -- tiger_counties --------------------------------------------------------
    op.create_table(
        "tiger_counties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("countyns", sa.String(length=8), nullable=True),
        sa.Column("geoid", sa.String(length=5), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("classfp", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("csafp", sa.String(length=3), nullable=True),
        sa.Column("cbsafp", sa.String(length=5), nullable=True),
        sa.Column("metdivfp", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_counties_geoid"),
        "tiger_counties",
        ["geoid"],
    )
    op.create_index(
        "ix_tiger_counties_geom",
        "tiger_counties",
        ["geom"],
        postgresql_using="gist",
    )

    # -- tiger_county_subdivisions ---------------------------------------------
    op.create_table(
        "tiger_county_subdivisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statefp", sa.String(length=2), nullable=True),
        sa.Column("countyfp", sa.String(length=3), nullable=True),
        sa.Column("cousubfp", sa.String(length=5), nullable=True),
        sa.Column("cousubns", sa.String(length=8), nullable=True),
        sa.Column("geoid", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("namelsad", sa.String(length=100), nullable=True),
        sa.Column("lsad", sa.String(length=2), nullable=True),
        sa.Column("classfp", sa.String(length=2), nullable=True),
        sa.Column("aland", sa.BigInteger(), nullable=True),
        sa.Column("awater", sa.BigInteger(), nullable=True),
        sa.Column("intptlat", sa.String(length=11), nullable=True),
        sa.Column("intptlon", sa.String(length=12), nullable=True),
        sa.Column("funcstat", sa.String(length=1), nullable=True),
        sa.Column("mtfcc", sa.String(length=5), nullable=True),
        sa.Column("cnectafp", sa.String(length=3), nullable=True),
        sa.Column("nectafp", sa.String(length=5), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, from_text="ST_GeomFromEWKT"
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
        op.f("ix_tiger_county_subdivisions_geoid"),
        "tiger_county_subdivisions",
        ["geoid"],
    )
    op.create_index(
        "ix_tiger_county_subdivisions_geom",
        "tiger_county_subdivisions",
        ["geom"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tiger_county_subdivisions_geom",
        table_name="tiger_county_subdivisions",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_county_subdivisions_geoid"),
        table_name="tiger_county_subdivisions",
    )
    op.drop_table("tiger_county_subdivisions")

    op.drop_index(
        "ix_tiger_counties_geom",
        table_name="tiger_counties",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_counties_geoid"),
        table_name="tiger_counties",
    )
    op.drop_table("tiger_counties")

    op.drop_index(
        "ix_tiger_school_districts_geom",
        table_name="tiger_school_districts",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_school_districts_geoid"),
        table_name="tiger_school_districts",
    )
    op.drop_index(
        op.f("ix_tiger_school_districts_district_type"),
        table_name="tiger_school_districts",
    )
    op.drop_table("tiger_school_districts")

    op.drop_index(
        "ix_tiger_tracts_geom",
        table_name="tiger_tracts",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_tracts_geoid"),
        table_name="tiger_tracts",
    )
    op.drop_table("tiger_tracts")

    op.drop_index(
        "ix_tiger_block_groups_geom",
        table_name="tiger_block_groups",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_block_groups_geoid"),
        table_name="tiger_block_groups",
    )
    op.drop_table("tiger_block_groups")

    op.drop_index(
        "ix_tiger_census_blocks_geom",
        table_name="tiger_census_blocks",
        postgresql_using="gist",
    )
    op.drop_index(
        op.f("ix_tiger_census_blocks_geoid20"),
        table_name="tiger_census_blocks",
    )
    op.drop_table("tiger_census_blocks")
