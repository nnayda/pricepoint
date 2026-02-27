"""DAG: Collect transportation noise data from BTS National Noise Map.

Manual-trigger DAG that downloads BTS noise map tiles for each mode
(aviation, road, rail, combined), vectorizes noise polygons by dB band,
stages them, applies PostGIS smoothing, and loads into the noises table.
"""

import logging
from datetime import datetime

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
        "retries": 0,
    },
    tags=["data", "collection", "bts", "noise"],
)
def bts_noise_collection():
    @task()
    def fetch_aviation():
        """Download aviation noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="aviation")
        logger.info("Loaded %d aviation noise polygons", count)

    @task()
    def fetch_road():
        """Download road noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="road")
        logger.info("Loaded %d road noise polygons", count)

    @task()
    def fetch_rail():
        """Download rail noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="rail")
        logger.info("Loaded %d rail noise polygons", count)

    @task()
    def fetch_combined():
        """Download combined aviation+road+rail noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="aviation_road_rail")
        logger.info("Loaded %d combined noise polygons", count)

    @task()
    def verify_load():
        """Verify that records were loaded into the noises table."""
        from pricepoint.data.geospatial.bts_noise import verify_transportation_noise

        verify_transportation_noise()

    [fetch_aviation(), fetch_road(), fetch_rail(), fetch_combined()] >> verify_load()


bts_noise_collection()
