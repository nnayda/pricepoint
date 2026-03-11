"""DAG: Collect subdivision boundaries from county ArcGIS sources.

Manual-trigger DAG that downloads subdivision polygons from configured county
ArcGIS MapServer endpoints into the gold ``subdivisions`` table.

Supersedes ``dag_wake_subdivision_collection.py``.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="subdivision_collection",
    description="Collect subdivision boundaries from county ArcGIS sources",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "subdivisions", "boundaries"],
)
def subdivision_collection():
    @task()
    def fetch():
        """Fetch subdivision boundaries for all configured counties."""
        from pricepoint.data.geospatial.subdivisions import fetch_subdivisions

        stats = fetch_subdivisions()
        logger.info("Subdivision collection stats: %s", stats)

    @task(outlets=[Asset("subdivision_boundaries")])
    def verify():
        """Verify that subdivision records were loaded for each county."""
        from pricepoint.data.geospatial.subdivisions import verify_subdivisions

        verify_subdivisions()

    fetch() >> verify()


subdivision_collection()
