"""DAG: Collect Wake County railroad features.

Manual-trigger DAG that downloads railroad data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_railroad_collection",
    description="Load Wake County railroad features into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "railroads", "transportation"],
)
def wake_railroad_collection():
    @task()
    def fetch_data():
        """Fetch Wake County railroad features."""
        from pricepoint.data.geospatial.wake_transportation import fetch_railroads

        fetch_railroads()

    @task()
    def verify_load():
        """Verify that railroad records were loaded."""
        from pricepoint.data.geospatial.wake_transportation import verify_railroads

        verify_railroads()

    fetch_data() >> verify_load()


wake_railroad_collection()
