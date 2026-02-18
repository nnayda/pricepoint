"""DAG: Collect Wake County library locations.

Manual-trigger DAG that downloads library data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_library_collection",
    description="Load Wake County library locations into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "libraries", "amenities"],
)
def wake_library_collection():
    @task()
    def fetch_data():
        """Fetch Wake County library locations."""
        from pricepoint.data.geospatial.wake_amenities import fetch_libraries

        fetch_libraries()

    @task()
    def verify_load():
        """Verify that library records were loaded."""
        from pricepoint.data.geospatial.wake_amenities import verify_libraries

        verify_libraries()

    fetch_data() >> verify_load()


wake_library_collection()
