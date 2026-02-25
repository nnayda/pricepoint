"""DAG: Collect transportation noise data from BTS National Noise Map.

Manual-trigger DAG that downloads BTS noise map tiles, vectorizes noise
polygons by dB band, and loads them into the noises table.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="bts_noise_collection",
    description="Load BTS transportation noise polygons into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "bts", "noise"],
)
def bts_noise_collection():
    @task()
    def fetch_noise():
        """Download BTS noise tiles, vectorize, and load into PostGIS."""
        from pricepoint.data.geospatial.bts_noise import (
            fetch_transportation_noise,
        )

        count = fetch_transportation_noise()
        logger.info("Loaded %d noise polygons", count)

    @task()
    def verify_load():
        """Verify that records were loaded into the noises table."""
        from pricepoint.data.geospatial.bts_noise import verify_transportation_noise

        verify_transportation_noise()

    fetch_noise() >> verify_load()


bts_noise_collection()
