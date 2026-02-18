"""DAG: Collect Wake County greenway trails.

Manual-trigger DAG that downloads greenway trail data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_greenway_collection",
    description="Load Wake County greenway trails into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "greenways"],
)
def wake_greenway_collection():
    @task()
    def fetch_data():
        """Fetch Wake County greenway trails."""
        from pricepoint.data.geospatial.wake_greenways import fetch_wake_greenways

        fetch_wake_greenways()

    @task()
    def verify_load():
        """Verify that Wake County greenway records were loaded."""
        from pricepoint.data.geospatial.wake_greenways import verify_wake_greenways

        verify_wake_greenways()

    fetch_data() >> verify_load()


wake_greenway_collection()
