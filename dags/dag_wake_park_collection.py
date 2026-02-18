"""DAG: Collect Wake County park boundaries.

Manual-trigger DAG that downloads park boundary data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_park_collection",
    description="Load Wake County park boundaries into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "parks"],
)
def wake_park_collection():
    @task()
    def fetch_data():
        """Fetch Wake County park boundaries."""
        from pricepoint.data.geospatial.wake_parks import fetch_wake_parks

        fetch_wake_parks()

    @task()
    def verify_load():
        """Verify that Wake County park records were loaded."""
        from pricepoint.data.geospatial.wake_parks import verify_wake_parks

        verify_wake_parks()

    fetch_data() >> verify_load()


wake_park_collection()
