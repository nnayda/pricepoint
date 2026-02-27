"""Rename TIGER tables to shorter names.

Revision ID: j2k4l6m8n0p2
Revises: i1j3k5l7m9n1
Create Date: 2026-02-27

"""

from alembic import op

revision = "j2k4l6m8n0p2"
down_revision = "i1j3k5l7m9n1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename tables
    op.rename_table("tiger_census_blocks", "blocks")
    op.rename_table("tiger_block_groups", "block_groups")
    op.rename_table("tiger_tracts", "tracts")
    op.rename_table("tiger_school_districts", "school_districts")
    op.rename_table("tiger_counties", "counties")
    op.rename_table("tiger_county_subdivisions", "townships")

    # Rename B-tree indexes
    op.execute("ALTER INDEX ix_tiger_census_blocks_geoid20 RENAME TO ix_blocks_geoid20")
    op.execute("ALTER INDEX ix_tiger_block_groups_geoid RENAME TO ix_block_groups_geoid")
    op.execute("ALTER INDEX ix_tiger_tracts_geoid RENAME TO ix_tracts_geoid")
    op.execute("ALTER INDEX ix_tiger_school_districts_geoid RENAME TO ix_school_districts_geoid")
    op.execute(
        "ALTER INDEX ix_tiger_school_districts_district_type"
        " RENAME TO ix_school_districts_district_type"
    )
    op.execute("ALTER INDEX ix_tiger_counties_geoid RENAME TO ix_counties_geoid")
    op.execute("ALTER INDEX ix_tiger_county_subdivisions_geoid RENAME TO ix_townships_geoid")

    # Rename GiST spatial indexes
    op.execute("ALTER INDEX ix_tiger_census_blocks_geom RENAME TO ix_blocks_geom")
    op.execute("ALTER INDEX ix_tiger_block_groups_geom RENAME TO ix_block_groups_geom")
    op.execute("ALTER INDEX ix_tiger_tracts_geom RENAME TO ix_tracts_geom")
    op.execute("ALTER INDEX idx_tiger_school_districts_geom RENAME TO idx_school_districts_geom")
    op.execute("ALTER INDEX ix_tiger_counties_geom RENAME TO ix_counties_geom")
    op.execute("ALTER INDEX ix_tiger_county_subdivisions_geom RENAME TO ix_townships_geom")


def downgrade() -> None:
    # Reverse table renames
    op.rename_table("blocks", "tiger_census_blocks")
    op.rename_table("block_groups", "tiger_block_groups")
    op.rename_table("tracts", "tiger_tracts")
    op.rename_table("school_districts", "tiger_school_districts")
    op.rename_table("counties", "tiger_counties")
    op.rename_table("townships", "tiger_county_subdivisions")

    # Reverse B-tree index renames
    op.execute("ALTER INDEX ix_blocks_geoid20 RENAME TO ix_tiger_census_blocks_geoid20")
    op.execute("ALTER INDEX ix_block_groups_geoid RENAME TO ix_tiger_block_groups_geoid")
    op.execute("ALTER INDEX ix_tracts_geoid RENAME TO ix_tiger_tracts_geoid")
    op.execute("ALTER INDEX ix_school_districts_geoid RENAME TO ix_tiger_school_districts_geoid")
    op.execute(
        "ALTER INDEX ix_school_districts_district_type"
        " RENAME TO ix_tiger_school_districts_district_type"
    )
    op.execute("ALTER INDEX ix_counties_geoid RENAME TO ix_tiger_counties_geoid")
    op.execute("ALTER INDEX ix_townships_geoid RENAME TO ix_tiger_county_subdivisions_geoid")

    # Reverse GiST index renames
    op.execute("ALTER INDEX ix_blocks_geom RENAME TO ix_tiger_census_blocks_geom")
    op.execute("ALTER INDEX ix_block_groups_geom RENAME TO ix_tiger_block_groups_geom")
    op.execute("ALTER INDEX ix_tracts_geom RENAME TO ix_tiger_tracts_geom")
    op.execute("ALTER INDEX idx_school_districts_geom RENAME TO idx_tiger_school_districts_geom")
    op.execute("ALTER INDEX ix_counties_geom RENAME TO ix_tiger_counties_geom")
    op.execute("ALTER INDEX ix_townships_geom RENAME TO ix_tiger_county_subdivisions_geom")
