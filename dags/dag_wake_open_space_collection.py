"""DAG: Collect Wake County open space boundaries.

Manual-trigger DAG that downloads open space boundary data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_open_space_collection",
    description="Load Wake County open space boundaries into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "open_space"],
)
def wake_open_space_collection():
    @task()
    def fetch_data():
        """Fetch Wake County open space boundaries."""
        from pricepoint.data.geospatial.wake_open_space import fetch_wake_open_space

        fetch_wake_open_space()

    @task()
    def verify_load():
        """Verify that Wake County open space records were loaded."""
        from pricepoint.data.geospatial.wake_open_space import verify_wake_open_space

        verify_wake_open_space()

    fetch_data() >> verify_load()


wake_open_space_collection()
