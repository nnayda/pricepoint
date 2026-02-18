"""DAG: Collect Raleigh park boundaries.

Manual-trigger DAG that downloads park boundary data from Raleigh into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="raleigh_park_collection",
    description="Load Raleigh park boundaries into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "raleigh", "parks"],
)
def raleigh_park_collection():
    @task()
    def fetch_data():
        """Fetch Raleigh park boundaries."""
        from pricepoint.data.geospatial.wake_parks import fetch_raleigh_parks

        fetch_raleigh_parks()

    @task()
    def verify_load():
        """Verify that Raleigh park records were loaded."""
        from pricepoint.data.geospatial.wake_parks import verify_raleigh_parks

        verify_raleigh_parks()

    fetch_data() >> verify_load()


raleigh_park_collection()
