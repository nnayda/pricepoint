"""DAG: Collect Wake County farmers market locations.

Manual-trigger DAG that downloads farmers market data from Wake County into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_farmers_market_collection",
    description="Load Wake County farmers market locations into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "wake", "farmers-markets", "amenities"],
)
def wake_farmers_market_collection():
    @task()
    def fetch_data():
        """Fetch Wake County farmers market locations."""
        from pricepoint.data.geospatial.wake_amenities import fetch_farmers_markets

        fetch_farmers_markets()

    @task()
    def verify_load():
        """Verify that farmers market records were loaded."""
        from pricepoint.data.geospatial.wake_amenities import verify_farmers_markets

        verify_farmers_markets()

    fetch_data() >> verify_load()


wake_farmers_market_collection()
