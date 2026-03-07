"""DAG: Collect Overture Maps Places.

Manual-trigger DAG that downloads commercial POIs from the Overture Maps
GeoParquet dataset on S3 and loads them into PostGIS.
"""

import logging
from datetime import datetime

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="overture_places_collection",
    description="Load Overture Maps Places into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "overture", "places", "pois"],
)
def overture_places_collection():
    @task()
    def fetch_places():
        """Fetch places from S3 GeoParquet."""
        from pricepoint.data.geospatial.overture_places import fetch_places

        fetch_places()

    @task()
    def verify_places():
        """Verify that place records were loaded."""
        from pricepoint.data.geospatial.overture_places import verify_places

        verify_places()

    @task()
    def refresh_place_names():
        """Rebuild the place_names autocomplete lookup table."""
        from pricepoint.data.geospatial.place_names import (
            refresh_place_names as _refresh,
        )

        _refresh()

    fetch_places() >> verify_places() >> refresh_place_names()


overture_places_collection()
