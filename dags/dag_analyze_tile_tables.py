"""DAG: ANALYZE tile-serving tables after data loads.

Auto-triggered DAG that runs PostgreSQL ANALYZE on all tables and views
served by the Martin tile server.  Without up-to-date statistics the
query planner cannot use spatial (GiST) indexes effectively, causing
slow tile generation and startup timeouts in Martin.

Fires whenever ANY upstream data-loading DAG emits an asset that feeds
a Martin tile source (direct table or underlying table of a view).
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, AssetAny, dag, task

logger = logging.getLogger(__name__)

# Tables that Martin serves directly as tile sources
TILE_TABLES = [
    "greenspaces",
    "trails",
    "noises",
    "risk_boundaries",
    "school_districts",
]

# Tables underlying the v_infrastructure view
INFRASTRUCTURE_TABLES = [
    "airports",
    "cell_towers",
    "transmission_lines",
    "power_plants",
    "nat_gas_pipelines",
    "petroleum_pipelines",
    "railroads",
    "roads",
]

# Tables underlying the demographic choropleth views
DEMOGRAPHIC_TABLES = [
    "block_groups",
    "tracts",
    "counties",
    "townships",
    "subdivisions",
    "acs_demographics",
    "acs_detailed_race",
]

ALL_TABLES = TILE_TABLES + INFRASTRUCTURE_TABLES + DEMOGRAPHIC_TABLES


@dag(
    dag_id="analyze_tile_tables",
    description="Run ANALYZE on Martin tile-serving tables after data loads",
    schedule=AssetAny(
        # Direct tile tables
        Asset("greenspaces"),
        Asset("trails"),
        Asset("noises"),
        Asset("risk_boundaries"),
        # Infrastructure (feeds v_infrastructure view)
        Asset("cell_towers"),
        Asset("transmission_lines"),
        Asset("power_plants"),
        Asset("nat_gas_pipelines"),
        Asset("petroleum_pipelines"),
        Asset("airports"),
        Asset("roads"),
        # Boundaries (feeds demographic views)
        Asset("geo_boundaries"),
        Asset("subdivision_boundaries"),
        Asset("demographics"),
        Asset("detailed_race"),
    ),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["maintenance", "tiles", "analyze"],
)
def analyze_tile_tables():
    @task()
    def analyze():
        """Run ANALYZE on all tile-serving tables."""
        from sqlalchemy import text

        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            for table in ALL_TABLES:
                logger.info("ANALYZE %s", table)
                session.execute(text(f"ANALYZE {table}"))  # noqa: S608
            session.commit()
            logger.info("ANALYZE complete for %d tables", len(ALL_TABLES))
        finally:
            session.close()

    analyze()


analyze_tile_tables()
