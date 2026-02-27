"""Add Martin tileserver database views.

Creates views for Martin vector tile serving:
- v_infrastructure: unions all infrastructure tables
- v_tract_demographics: joins tracts with ACS data
- v_block_group_demographics: joins block groups with ACS data

Revision ID: a1b2c3d4e5f6
Revises: z3a5b7c9d1e3
Create Date: 2026-02-27

"""

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "z3a5b7c9d1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW v_infrastructure AS
        SELECT id::text AS feature_id, 'cell_tower' AS infra_type, geom,
               NULL::text AS name
        FROM cell_towers
        UNION ALL
        SELECT id::text, 'transmission_line', geom, NULL
        FROM transmission_lines
        UNION ALL
        SELECT id::text, 'power_plant', geom, name
        FROM power_plants
        UNION ALL
        SELECT id::text, 'nat_gas_pipeline', geom, NULL
        FROM nat_gas_pipelines
        UNION ALL
        SELECT id::text, 'petroleum_pipeline', geom, NULL
        FROM petroleum_pipelines
        UNION ALL
        SELECT id::text, 'railroad', geom, COALESCE(rrowner1, 'Railroad')
        FROM railroads
        UNION ALL
        SELECT id::text, 'airport', geom, name
        FROM airports
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_tract_demographics AS
        SELECT t.id, t.geoid, t.geom,
               d.total_population, d.median_household_income,
               d.white_pct, d.black_pct, d.hispanic_pct, d.asian_pct,
               d.median_age
        FROM tracts t
        LEFT JOIN acs_demographics d
            ON t.geoid = d.geoid AND d.geo_level = 'tract'
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_block_group_demographics AS
        SELECT bg.id, bg.geoid, bg.geom,
               d.total_population, d.median_household_income,
               d.white_pct, d.black_pct, d.hispanic_pct, d.asian_pct,
               d.median_age
        FROM block_groups bg
        LEFT JOIN acs_demographics d
            ON bg.geoid = d.geoid AND d.geo_level = 'block_group'
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_block_group_demographics")
    op.execute("DROP VIEW IF EXISTS v_tract_demographics")
    op.execute("DROP VIEW IF EXISTS v_infrastructure")
