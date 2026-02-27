"""DAG: Collect USGS National Digital Trails.

Manual-trigger DAG that downloads trail data from the USGS National Map
ArcGIS endpoint into PostGIS.
"""

import logging
from datetime import datetime

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="usgs_trail_collection",
    description="Load USGS National Digital Trails into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "usgs", "trails"],
)
def usgs_trail_collection():
    @task()
    def fetch_data():
        """Fetch USGS trails."""
        from pricepoint.data.geospatial.trails import fetch_trails

        fetch_trails()

    @task()
    def verify_load():
        """Verify that trail records were loaded."""
        from pricepoint.data.geospatial.trails import verify_trails

        verify_trails()

    fetch_data() >> verify_load()


usgs_trail_collection()
