"""DAG: Collect Wake County utility easement features.

Manual-trigger DAG that downloads utility easement data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_utility_easement_collection",
    description="Load Wake County utility easement features into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "utility-easements"],
)
def wake_utility_easement_collection():
    @task()
    def fetch_data():
        """Fetch Wake County utility easement features."""
        from pricepoint.data.geospatial.wake_transportation import fetch_utility_easements

        fetch_utility_easements()

    @task()
    def verify_load():
        """Verify that utility easement records were loaded."""
        from pricepoint.data.geospatial.wake_transportation import verify_utility_easements

        verify_utility_easements()

    fetch_data() >> verify_load()


wake_utility_easement_collection()
