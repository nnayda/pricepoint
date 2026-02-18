"""DAG: Collect Wake County hospital locations.

Manual-trigger DAG that downloads hospital data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_hospital_collection",
    description="Load Wake County hospital locations into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "hospitals", "amenities"],
)
def wake_hospital_collection():
    @task()
    def fetch_data():
        """Fetch Wake County hospital locations."""
        from pricepoint.data.geospatial.wake_amenities import fetch_hospitals

        fetch_hospitals()

    @task()
    def verify_load():
        """Verify that hospital records were loaded."""
        from pricepoint.data.geospatial.wake_amenities import verify_hospitals

        verify_hospitals()

    fetch_data() >> verify_load()


wake_hospital_collection()
