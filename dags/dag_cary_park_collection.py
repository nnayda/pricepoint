"""DAG: Collect Cary park locations.

Manual-trigger DAG that downloads park location data from Cary into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="cary_park_collection",
    description="Load Cary park locations into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "cary", "parks"],
)
def cary_park_collection():
    @task()
    def fetch_data():
        """Fetch Cary park locations."""
        from pricepoint.data.geospatial.wake_parks import fetch_cary_parks

        fetch_cary_parks()

    @task()
    def verify_load():
        """Verify that Cary park records were loaded."""
        from pricepoint.data.geospatial.wake_parks import verify_cary_parks

        verify_cary_parks()

    fetch_data() >> verify_load()


cary_park_collection()
