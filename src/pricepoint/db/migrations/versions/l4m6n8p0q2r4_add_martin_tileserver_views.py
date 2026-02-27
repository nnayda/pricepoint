"""Add Martin tileserver database views.

Creates views for Martin vector tile serving:
- v_infrastructure: unions all infrastructure tables
- v_tract_demographics: joins tracts with ACS data
- v_block_group_demographics: joins block groups with ACS data

Revision ID: l4m6n8p0q2r4
Revises: k3l5m7n9p1q3
Create Date: 2026-02-27

"""

from alembic import op

revision = "l4m6n8p0q2r4"
down_revision = "k3l5m7n9p1q3"
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
        UNION ALL
        SELECT id::text, 'road', geom, fullname
        FROM roads
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_tract_demographics AS
        SELECT t.id, t.geoid, t.geom,
               d.total_population, d.median_household_income,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_white * 100.0 / d.total_population, 1)
               END AS white_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_black * 100.0 / d.total_population, 1)
               END AS black_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.hispanic * 100.0 / d.total_population, 1)
               END AS hispanic_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_asian * 100.0 / d.total_population, 1)
               END AS asian_pct,
               d.median_age
        FROM tracts t
        LEFT JOIN acs_demographics d
            ON t.geoid = d.geoid AND d.geography_level = 'tract'
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_block_group_demographics AS
        SELECT bg.id, bg.geoid, bg.geom,
               d.total_population, d.median_household_income,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_white * 100.0 / d.total_population, 1)
               END AS white_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_black * 100.0 / d.total_population, 1)
               END AS black_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.hispanic * 100.0 / d.total_population, 1)
               END AS hispanic_pct,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_asian * 100.0 / d.total_population, 1)
               END AS asian_pct,
               d.median_age
        FROM block_groups bg
        LEFT JOIN acs_demographics d
            ON bg.geoid = d.geoid AND d.geography_level = 'block_group'
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_block_group_demographics")
    op.execute("DROP VIEW IF EXISTS v_tract_demographics")
    op.execute("DROP VIEW IF EXISTS v_infrastructure")
