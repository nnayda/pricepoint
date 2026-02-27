"""DAG: Collect Census ACS 5-Year demographic estimates.

Manual-trigger DAG that downloads population, age, race, income, education,
home ownership, and home value data at multiple geographic levels for
multiple non-overlapping ACS vintages into PostGIS.

Data is fetched nationwide (all 50 US states + DC) for each geography level.

Levels: national, state, county, county subdivision, tract, block group,
and Wake subdivision (area-weighted from block groups).
"""

import logging
from datetime import datetime

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
        "retries": 0,
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
    def fetch_summary_demographics():
        """Fetch ACS national, state, and county demographics for all vintages."""
        from pricepoint.data.geospatial.census_demographics import (
            fetch_acs_summary_demographics,
        )

        fetch_acs_summary_demographics()

    @task()
    def fetch_county_sub_demographics():
        """Fetch ACS county subdivision demographics for all vintages."""
        from pricepoint.data.geospatial.census_demographics import (
            fetch_acs_county_sub_demographics,
        )

        fetch_acs_county_sub_demographics()

    @task()
    def compute_subdivision_demo():
        """Compute Wake subdivision demographics from block group data."""
        from pricepoint.data.geospatial.census_demographics import (
            compute_subdivision_demographics,
        )

        compute_subdivision_demographics()

    @task()
    def verify_load():
        """Verify that ACS demographic records were loaded."""
        from pricepoint.data.geospatial.census_demographics import (
            verify_acs_demographics,
        )

        verify_acs_demographics()

    t_tract = fetch_tract_demographics()
    t_bg = fetch_block_group_demographics()
    t_summary = fetch_summary_demographics()
    t_cousub = fetch_county_sub_demographics()
    t_subdiv = compute_subdivision_demo()
    t_verify = verify_load()

    # Block group data must be ready before subdivision computation
    t_bg >> t_subdiv

    # All tasks must complete before verification
    [t_tract, t_bg, t_summary, t_cousub, t_subdiv] >> t_verify


census_demographic_collection()
