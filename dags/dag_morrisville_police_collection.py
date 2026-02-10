"""DAG: Collect Morrisville police incident data from the Town of Morrisville Open Data Portal.

Runs weekly to truncate and reload the staging table with all incident records.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="morrisville_police_collection",
    description="Weekly full refresh of Morrisville police incident staging data",
    schedule="@weekly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "morrisville", "police"],
)
def morrisville_police_collection():
    @task()
    def fetch_morrisville_incidents():
        """Fetch all Morrisville police incident records (truncate + reload)."""
        from pricepoint.data.geospatial.police_incidents import (
            fetch_morrisville_police_incidents,
        )

        fetch_morrisville_police_incidents(full_refresh=True)

    @task()
    def verify_load():
        """Verify that records were loaded into the staging table."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingMorrisvillePoliceIncident

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(StagingMorrisvillePoliceIncident)
            ).scalar()
            if not count:
                msg = "No records found in staging_morrisville_police_incidents after load"
                raise RuntimeError(msg)
            logger.info("Verified %d Morrisville police incident records", count)
        finally:
            session.close()

    fetch_morrisville_incidents() >> verify_load()


morrisville_police_collection()
