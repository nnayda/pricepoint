"""DAG: Collect airport data from OurAirports.

Manual-trigger DAG that downloads the OurAirports CSV and loads US
airports into the airports table via direct upsert.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="ourairports_collection",
    description="Load US airport data from OurAirports CSV into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "ourairports", "airports"],
)
def ourairports_collection():
    @task()
    def fetch_airports():
        """Fetch airport data from OurAirports CSV."""
        from pricepoint.data.geospatial.ourairports import (
            fetch_airports as _fetch_airports,
        )

        count = _fetch_airports()
        logger.info("Loaded %d airports", count)

    @task(outlets=[Asset("airports")])
    def verify_load():
        """Verify that records were loaded into the airports table."""
        from pricepoint.data.geospatial.ourairports import verify_airports

        verify_airports()

    fetch_airports() >> verify_load()


ourairports_collection()
