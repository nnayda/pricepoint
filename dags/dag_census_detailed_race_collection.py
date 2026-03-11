"""DAG: Collect Census ACS detailed race sub-group estimates.

Manual-trigger DAG that downloads Asian sub-group population data
(Census table B02015) at multiple geographic levels for the latest
ACS vintage into PostGIS.

Designed to support future race category breakdowns (Hispanic, Pacific Islander).
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="census_detailed_race_collection",
    description="Load ACS detailed race sub-group estimates into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "census", "demographic", "race"],
)
def census_detailed_race_collection():
    @task()
    def fetch_detailed_race():
        """Fetch B02015 Asian sub-group data for all geo levels."""
        from pricepoint.data.geospatial.census_demographics import (
            fetch_detailed_race_demographics,
        )

        fetch_detailed_race_demographics()

    @task()
    def compute_subdivision_detailed():
        """Compute subdivision detailed race from block group data."""
        from pricepoint.data.geospatial.census_demographics import (
            compute_subdivision_detailed_race,
        )

        compute_subdivision_detailed_race()

    @task(outlets=[Asset("detailed_race")])
    def verify_load():
        """Verify that detailed race records were loaded."""
        from pricepoint.data.geospatial.census_demographics import (
            verify_detailed_race_load,
        )

        verify_detailed_race_load()

    t1 = fetch_detailed_race()
    t2 = compute_subdivision_detailed()
    t3 = verify_load()

    t1 >> t2 >> t3


census_detailed_race_collection()
