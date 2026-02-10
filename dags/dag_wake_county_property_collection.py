"""Wake County property assessment data collection DAG.

Runs biweekly to download and load Wake County's daily property extract
into staging_wake_county_property_data table.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task
from sqlalchemy import func, select

logger = logging.getLogger(__name__)


@dag(
    dag_id="wake_county_property_collection",
    schedule="0 0 */14 * *",  # Biweekly at midnight
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "housing", "county"],
)
def wake_county_property_collection():
    """Wake County property data collection DAG (biweekly schedule)."""

    @task()
    def fetch_property_data():
        """Download and load Wake County property data into staging table."""
        from pricepoint.data.housing.wake_county_property import (
            fetch_wake_county_property_data,
        )

        fetch_wake_county_property_data()

    @task()
    def verify_load():
        """Verify records were loaded into staging table."""
        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingWakeCountyPropertyData

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(StagingWakeCountyPropertyData)
            ).scalar()

            if not count:
                raise RuntimeError("No records found in staging_wake_county_property_data")

            logger.info("Verification successful: %d records in staging table", count)

        finally:
            session.close()

    # Task dependency
    fetch_property_data() >> verify_load()


# Instantiate DAG
wake_county_property_collection()
