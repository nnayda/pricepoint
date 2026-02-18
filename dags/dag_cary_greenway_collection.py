"""DAG: Collect Cary greenway trails.

Manual-trigger DAG that downloads greenway trail data from Cary into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="cary_greenway_collection",
    description="Load Cary greenway trails into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "cary", "greenways"],
)
def cary_greenway_collection():
    @task()
    def fetch_data():
        """Fetch Cary greenway trails."""
        from pricepoint.data.geospatial.wake_greenways import fetch_cary_greenways

        fetch_cary_greenways()

    @task()
    def verify_load():
        """Verify that Cary greenway records were loaded."""
        from pricepoint.data.geospatial.wake_greenways import verify_cary_greenways

        verify_cary_greenways()

    fetch_data() >> verify_load()


cary_greenway_collection()
