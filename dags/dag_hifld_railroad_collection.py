"""DAG: Collect railroad data from HIFLD.

Manual-trigger DAG that downloads North American Rail Network lines
for the configured state and loads them into the railroads table.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="hifld_railroad_collection",
    description="Load railroad lines from HIFLD ArcGIS FeatureServer into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "hifld", "railroads"],
)
def hifld_railroad_collection():
    @task()
    def fetch_railroads():
        """Fetch railroad data from HIFLD ArcGIS FeatureServer."""
        from pricepoint.data.geospatial.hifld_railroads import (
            fetch_railroads as _fetch_railroads,
        )

        count = _fetch_railroads()
        logger.info("Loaded %d railroads", count)

    @task()
    def verify_load():
        """Verify that records were loaded into the railroads table."""
        from pricepoint.data.geospatial.hifld_railroads import verify_railroads

        verify_railroads()

    fetch_railroads() >> verify_load()


hifld_railroad_collection()
