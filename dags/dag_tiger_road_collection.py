"""DAG: Collect US Census TIGER/Line primary and secondary road shapefiles.

Manual-trigger DAG that downloads TIGER/Line PRISECROADS shapefiles for all
US states and loads primary (S1100) and secondary (S1200) road centerlines
into the ``roads`` PostGIS table.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="tiger_road_collection",
    description="Load TIGER/Line primary and secondary roads into PostGIS (all US states)",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "tiger", "roads"],
)
def tiger_road_collection():
    @task()
    def fetch_roads():
        """Fetch TIGER/Line primary and secondary roads for all US states."""
        from pricepoint.data.geospatial.tiger_roads import fetch_roads

        fetch_roads()

    @task()
    def verify_load():
        """Verify that records were loaded into the roads table."""
        from pricepoint.data.geospatial.tiger_roads import verify_roads

        verify_roads()

    fetch_roads() >> verify_load()


tiger_road_collection()
