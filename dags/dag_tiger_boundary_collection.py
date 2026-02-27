"""DAG: Collect US Census TIGER/Line boundary shapefiles.

Manual-trigger DAG that downloads TIGER/Line shapefiles for census blocks,
block groups, tracts, school districts, counties, and county subdivisions
into PostGIS tables.  Downloads data for all US states (50 states + DC).

Each state-level layer is processed one state at a time within its task to
keep memory usage manageable.  Counties use a single national file.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="tiger_boundary_collection",
    description="Load US Census TIGER/Line boundary shapefiles into PostGIS (all US states)",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "tiger", "boundaries", "census"],
)
def tiger_boundary_collection():
    @task()
    def fetch_census_blocks():
        """Fetch TIGER/Line census block boundaries for all US states."""
        from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_census_blocks

        fetch_tiger_census_blocks()

    @task()
    def fetch_block_groups():
        """Fetch TIGER/Line block group boundaries for all US states."""
        from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_block_groups

        fetch_tiger_block_groups()

    @task()
    def fetch_tracts():
        """Fetch TIGER/Line census tract boundaries for all US states."""
        from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_tracts

        fetch_tiger_tracts()

    @task()
    def fetch_school_districts():
        """Fetch TIGER/Line school district boundaries for all US states."""
        from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_school_districts

        fetch_tiger_school_districts()

    @task()
    def fetch_counties():
        """Fetch TIGER/Line county boundaries (national file)."""
        from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_counties

        fetch_tiger_counties()

    @task()
    def fetch_county_subdivisions():
        """Fetch TIGER/Line county subdivision boundaries for all US states."""
        from pricepoint.data.geospatial.tiger_boundaries import (
            fetch_tiger_county_subdivisions,
        )

        fetch_tiger_county_subdivisions()

    @task()
    def verify_load():
        """Verify that records were loaded into all TIGER boundary tables."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import (
            Block,
            BlockGroup,
            County,
            SchoolDistrict,
            Township,
            Tract,
        )

        session = SessionLocal()
        try:
            tables = [
                ("blocks", Block),
                ("block_groups", BlockGroup),
                ("tracts", Tract),
                ("school_districts", SchoolDistrict),
                ("counties", County),
                ("townships", Township),
            ]
            for table_name, model in tables:
                count = session.execute(select(func.count()).select_from(model)).scalar()
                if not count:
                    raise RuntimeError(f"No records found in {table_name} after load")
                logger.info("Verified %d records in %s", count, table_name)
        finally:
            session.close()

    (
        [
            fetch_census_blocks(),
            fetch_block_groups(),
            fetch_tracts(),
            fetch_school_districts(),
            fetch_counties(),
            fetch_county_subdivisions(),
        ]
        >> verify_load()
    )


tiger_boundary_collection()
