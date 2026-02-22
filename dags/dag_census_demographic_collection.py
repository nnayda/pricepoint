"""DAG: Collect Census ACS 5-Year demographic estimates.

Manual-trigger DAG that downloads population, age, race, income, education,
home ownership, and home value data at tract and block group levels for
multiple non-overlapping ACS vintages into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="census_demographic_collection",
    description="Load ACS 5-Year demographic estimates into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "census", "demographic"],
)
def census_demographic_collection():
    @task()
    def fetch_tract_demographics():
        """Fetch ACS tract-level demographics for all vintages."""
        from pricepoint.data.geospatial.census_demographics import (
            fetch_acs_tract_demographics,
        )

        fetch_acs_tract_demographics()

    @task()
    def fetch_block_group_demographics():
        """Fetch ACS block-group-level demographics for all vintages."""
        from pricepoint.data.geospatial.census_demographics import (
            fetch_acs_block_group_demographics,
        )

        fetch_acs_block_group_demographics()

    @task()
    def verify_load():
        """Verify that ACS demographic records were loaded."""
        from pricepoint.data.geospatial.census_demographics import (
            verify_acs_demographics,
        )

        verify_acs_demographics()

    [fetch_tract_demographics(), fetch_block_group_demographics()] >> verify_load()


census_demographic_collection()
