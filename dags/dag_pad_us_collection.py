"""DAG: Collect PAD-US protected areas / greenspace data.

Manual-trigger DAG that downloads the PAD-US GeoPackage from USGS
ScienceBase and upserts publicly accessible terrestrial features
into the greenspaces table.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="pad_us_collection",
    description="Load PAD-US protected areas into greenspaces table",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "pad-us", "greenspace"],
)
def pad_us_collection():
    @task()
    def fetch_data():
        """Download and upsert PAD-US Fee features."""
        from pricepoint.data.geospatial.pad_us import fetch_pad_us

        fetch_pad_us()

    @task(outlets=[Asset("greenspaces")])
    def verify_load():
        """Verify that greenspace records were loaded."""
        from pricepoint.data.geospatial.pad_us import verify_pad_us

        verify_pad_us()

    fetch_data() >> verify_load()


pad_us_collection()
