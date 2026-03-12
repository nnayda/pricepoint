"""DAG: Collect transportation noise data from BTS National Noise Map.

Manual-trigger DAG that downloads BTS noise map tiles for each mode
(aviation, road, rail, combined), vectorizes noise polygons by dB band,
stages them, applies PostGIS smoothing, and loads into the noises table.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

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
    def _get_bbox(**context: object) -> tuple[float, float, float, float] | None:
        """Extract optional bbox from dag_run.conf (south, north, west, east)."""
        params = context.get("params", {})
        raw = params.get("bbox") if isinstance(params, dict) else None  # type: ignore[union-attr]
        if raw is None:
            return None
        south, north, west, east = (float(v) for v in raw)
        return (south, north, west, east)

    @task()
    def fetch_aviation(**context: object):
        """Download aviation noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="aviation", bbox=_get_bbox(**context))
        logger.info("Loaded %d aviation noise polygons", count)

    @task()
    def fetch_road(**context: object):
        """Download road noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="road", bbox=_get_bbox(**context))
        logger.info("Loaded %d road noise polygons", count)

    @task()
    def fetch_rail(**context: object):
        """Download rail noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="rail", bbox=_get_bbox(**context))
        logger.info("Loaded %d rail noise polygons", count)

    @task()
    def fetch_combined(**context: object):
        """Download combined aviation+road+rail noise tiles, stage, smooth, and load."""
        from pricepoint.data.geospatial.bts_noise import fetch_transportation_noise

        count = fetch_transportation_noise(mode="aviation_road_rail", bbox=_get_bbox(**context))
        logger.info("Loaded %d combined noise polygons", count)

    @task(outlets=[Asset("noises")])
    def verify_load():
        """Verify that records were loaded into the noises table."""
        from pricepoint.data.geospatial.bts_noise import verify_transportation_noise

        verify_transportation_noise()

    [fetch_aviation(), fetch_road(), fetch_rail(), fetch_combined()] >> verify_load()


bts_noise_collection()
