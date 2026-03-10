"""DAG: Refresh place_names autocomplete lookup table.

Asset-triggered DAG that rebuilds the place_names table after Overture
Places data has been loaded.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="place_names_refresh",
    description="Rebuild place_names autocomplete lookup from Overture Places",
    schedule=[Asset("overture_places")],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
    },
    tags=["data", "transform", "places", "pois"],
)
def place_names_refresh():
    @task()
    def refresh_place_names():
        """Rebuild the place_names autocomplete lookup table."""
        from pricepoint.data.geospatial.place_names import (
            refresh_place_names as _refresh,
        )

        _refresh()

    @task()
    def verify_refresh():
        """Verify that place_names table has rows."""
        from pricepoint.db.engine import Session
        from sqlalchemy import text

        with Session() as session:
            count = session.execute(
                text("SELECT count(*) FROM place_names")
            ).scalar()
            logger.info("place_names table has %d rows", count)
            if not count:
                raise RuntimeError("place_names table is empty after refresh")

    refresh_place_names() >> verify_refresh()


place_names_refresh()
