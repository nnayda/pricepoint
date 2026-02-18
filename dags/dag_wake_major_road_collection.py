"""DAG: Collect Wake County major road features.

Manual-trigger DAG that downloads major road data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_major_road_collection",
    description="Load Wake County major road features into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "major-roads", "transportation"],
)
def wake_major_road_collection():
    @task()
    def fetch_data():
        """Fetch Wake County major road features."""
        from pricepoint.data.geospatial.wake_transportation import fetch_major_roads

        fetch_major_roads()

    @task()
    def verify_load():
        """Verify that major road records were loaded."""
        from pricepoint.data.geospatial.wake_transportation import verify_major_roads

        verify_major_roads()

    fetch_data() >> verify_load()


wake_major_road_collection()
