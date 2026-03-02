"""Fix demographics tileserver views for all geographic levels.

Recreates demographics views with:
- acs_year filter (latest vintage only) to avoid duplicate geometries
- home_ownership_rate column for ownership choropleth
- name column for map labels
- New views for counties, townships, and subdivisions

Revision ID: m5n7p9q1r3s5
Revises: l4m6n8p0q2r4
Create Date: 2026-03-02

"""

from alembic import op

revision = "m5n7p9q1r3s5"
down_revision = "l4m6n8p0q2r4"
branch_labels = None
depends_on = None


# Common demographic columns selected from ACS join
# Column names must match frontend tile property expectations:
#   population, median_income, median_age, home_ownership_rate,
#   pct_white, pct_black, pct_hispanic, pct_asian, pct_other,
#   dominant_race, dominant_race_pct
_DEMO_COLS = """
               d.total_population AS population,
               d.median_household_income AS median_income,
               d.median_age,
               CASE WHEN d.housing_total_occupied > 0
                    THEN round(d.housing_owner_occupied * 100.0
                               / d.housing_total_occupied, 1)::float8
               END AS home_ownership_rate,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_white * 100.0 / d.total_population, 1)::float8
               END AS pct_white,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_black * 100.0 / d.total_population, 1)::float8
               END AS pct_black,
               CASE WHEN d.total_population > 0
                    THEN round(d.hispanic * 100.0 / d.total_population, 1)::float8
               END AS pct_hispanic,
               CASE WHEN d.total_population > 0
                    THEN round(d.race_asian * 100.0 / d.total_population, 1)::float8
               END AS pct_asian,
               CASE WHEN d.total_population > 0
                    THEN round(
                        (d.total_population
                         - COALESCE(d.race_white, 0)
                         - COALESCE(d.race_black, 0)
                         - COALESCE(d.hispanic, 0)
                         - COALESCE(d.race_asian, 0)
                        ) * 100.0 / d.total_population, 1)::float8
               END AS pct_other,
               CASE WHEN d.total_population > 0 THEN
                    (SELECT r.race FROM (VALUES
                        (d.race_white, 'White'),
                        (d.race_black, 'Black'),
                        (d.hispanic, 'Hispanic'),
                        (d.race_asian, 'Asian'),
                        (d.total_population
                         - COALESCE(d.race_white, 0)
                         - COALESCE(d.race_black, 0)
                         - COALESCE(d.hispanic, 0)
                         - COALESCE(d.race_asian, 0), 'Other')
                    ) AS r(cnt, race) ORDER BY r.cnt DESC NULLS LAST LIMIT 1)
               END AS dominant_race,
               CASE WHEN d.total_population > 0 THEN
                    round(
                        GREATEST(
                            COALESCE(d.race_white, 0),
                            COALESCE(d.race_black, 0),
                            COALESCE(d.hispanic, 0),
                            COALESCE(d.race_asian, 0),
                            d.total_population
                             - COALESCE(d.race_white, 0)
                             - COALESCE(d.race_black, 0)
                             - COALESCE(d.hispanic, 0)
                             - COALESCE(d.race_asian, 0)
                        ) * 100.0 / d.total_population, 1)::float8
               END AS dominant_race_pct"""


def upgrade() -> None:
    # Drop label views first (they depend on demographic views)
    op.execute("DROP VIEW IF EXISTS v_tract_labels")
    op.execute("DROP VIEW IF EXISTS v_block_group_labels")
    op.execute("DROP VIEW IF EXISTS v_county_labels")
    op.execute("DROP VIEW IF EXISTS v_township_labels")
    op.execute("DROP VIEW IF EXISTS v_subdivision_labels")
    # Drop demographic views — CREATE OR REPLACE cannot reorder/rename columns
    op.execute("DROP VIEW IF EXISTS v_tract_demographics")
    op.execute("DROP VIEW IF EXISTS v_block_group_demographics")
    op.execute("DROP VIEW IF EXISTS v_county_demographics")
    op.execute("DROP VIEW IF EXISTS v_township_demographics")
    op.execute("DROP VIEW IF EXISTS v_subdivision_demographics")

    # -- Tract demographics --------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_tract_demographics AS
        SELECT t.id, t.geoid, t.geom,
               COALESCE(t.namelsad, t.name, t.geoid) AS name,
               {_DEMO_COLS}
        FROM tracts t
        LEFT JOIN acs_demographics d
            ON t.geoid = d.geoid
           AND d.geography_level = 'tract'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'tract'
           )
    """)

    # -- Block group demographics --------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_block_group_demographics AS
        SELECT bg.id, bg.geoid, bg.geom,
               COALESCE(bg.namelsad, bg.geoid) AS name,
               {_DEMO_COLS}
        FROM block_groups bg
        LEFT JOIN acs_demographics d
            ON bg.geoid = d.geoid
           AND d.geography_level = 'block_group'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'block_group'
           )
    """)

    # -- County demographics -------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_county_demographics AS
        SELECT c.id, c.geoid, c.geom,
               COALESCE(c.namelsad, c.name, c.geoid) AS name,
               {_DEMO_COLS}
        FROM counties c
        LEFT JOIN acs_demographics d
            ON c.geoid = d.geoid
           AND d.geography_level = 'county'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'county'
           )
    """)

    # -- Township (county subdivision) demographics --------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_township_demographics AS
        SELECT tw.id, tw.geoid, tw.geom,
               COALESCE(tw.namelsad, tw.name, tw.geoid) AS name,
               {_DEMO_COLS}
        FROM townships tw
        LEFT JOIN acs_demographics d
            ON tw.geoid = d.geoid
           AND d.geography_level = 'county_subdivision'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'county_subdivision'
           )
    """)

    # -- Subdivision demographics --------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE VIEW v_subdivision_demographics AS
        SELECT s.id,
               ('subdiv_' || s.id::text) AS geoid,
               s.geom,
               COALESCE(s.name, 'Subdivision ' || s.id::text) AS name,
               {_DEMO_COLS}
        FROM subdivisions s
        LEFT JOIN acs_demographics d
            ON d.geoid = 'subdiv_' || s.id::text
           AND d.geography_level = 'subdivision'
           AND d.acs_year = (
               SELECT max(acs_year) FROM acs_demographics
               WHERE geography_level = 'subdivision'
           )
    """)

    # -- Label point views (one point per region → no tile-boundary duplication) --
    _LABEL_VIEWS = {
        "v_tract_labels": "v_tract_demographics",
        "v_block_group_labels": "v_block_group_demographics",
        "v_county_labels": "v_county_demographics",
        "v_township_labels": "v_township_demographics",
        "v_subdivision_labels": "v_subdivision_demographics",
    }
    for label_view, source_view in _LABEL_VIEWS.items():
        op.execute(f"""
            CREATE OR REPLACE VIEW {label_view} AS
            SELECT id, geoid,
                   ST_PointOnSurface(geom) AS geom,
                   name,
                   population,
                   median_income,
                   median_age,
                   home_ownership_rate,
                   pct_white, pct_black, pct_hispanic, pct_asian, pct_other,
                   dominant_race, dominant_race_pct
            FROM {source_view}
        """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_subdivision_labels")
    op.execute("DROP VIEW IF EXISTS v_township_labels")
    op.execute("DROP VIEW IF EXISTS v_county_labels")
    op.execute("DROP VIEW IF EXISTS v_block_group_labels")
    op.execute("DROP VIEW IF EXISTS v_tract_labels")
    op.execute("DROP VIEW IF EXISTS v_subdivision_demographics")
    op.execute("DROP VIEW IF EXISTS v_township_demographics")
    op.execute("DROP VIEW IF EXISTS v_county_demographics")

    # Restore original views (without acs_year filter, without name/ownership)
    op.execute("DROP VIEW IF EXISTS v_tract_demographics")
    op.execute("DROP VIEW IF EXISTS v_block_group_demographics")
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
