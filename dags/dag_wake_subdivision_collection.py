"""DAG: Collect Wake County subdivision boundaries.

.. deprecated::
    Superseded by ``dag_subdivision_collection.py`` which uses the generic
    multi-county collector.  This file is kept for reference only.

Manual-trigger DAG that downloads subdivision polygons from the Wake County
ArcGIS MapServer into PostGIS.
"""

import logging
from datetime import datetime

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_subdivision_collection",
    description="Load Wake County subdivision boundaries into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "wake", "subdivisions", "boundaries"],
)
def wake_subdivision_collection():
    @task()
    def fetch_subdivisions():
        """Fetch Wake County subdivision boundaries."""
        from pricepoint.data.geospatial.wake_subdivisions import fetch_wake_subdivisions

        fetch_wake_subdivisions()

    @task()
    def verify_load():
        """Verify that subdivision records were loaded."""
        from pricepoint.data.geospatial.wake_subdivisions import verify_wake_subdivisions

        verify_wake_subdivisions()

    fetch_subdivisions() >> verify_load()


wake_subdivision_collection()
