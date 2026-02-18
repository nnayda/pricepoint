"""DAG: Collect Wake County highway features.

Manual-trigger DAG that downloads highway data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_highway_collection",
    description="Load Wake County highway features into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "highways", "transportation"],
)
def wake_highway_collection():
    @task()
    def fetch_data():
        """Fetch Wake County highway features."""
        from pricepoint.data.geospatial.wake_transportation import fetch_highways

        fetch_highways()

    @task()
    def verify_load():
        """Verify that highway records were loaded."""
        from pricepoint.data.geospatial.wake_transportation import verify_highways

        verify_highways()

    fetch_data() >> verify_load()


wake_highway_collection()
