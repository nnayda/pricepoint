"""DAG: Collect Raleigh greenway trails.

Manual-trigger DAG that downloads greenway trail data from Raleigh into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="raleigh_greenway_collection",
    description="Load Raleigh greenway trails into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "raleigh", "greenways"],
)
def raleigh_greenway_collection():
    @task()
    def fetch_data():
        """Fetch Raleigh greenway trails."""
        from pricepoint.data.geospatial.wake_greenways import fetch_raleigh_greenways

        fetch_raleigh_greenways()

    @task()
    def verify_load():
        """Verify that Raleigh greenway records were loaded."""
        from pricepoint.data.geospatial.wake_greenways import verify_raleigh_greenways

        verify_raleigh_greenways()

    fetch_data() >> verify_load()


raleigh_greenway_collection()
