"""DAG: Collect Raleigh police incident data from ArcGIS Feature Services.

Runs daily to fetch the previous day's incidents and append to the staging table.
"""

import logging
from datetime import datetime

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="raleigh_police_collection",
    description="Daily incremental load of Raleigh police incident staging data",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "raleigh", "police"],
)
def raleigh_police_collection():
    @task()
    def fetch_daily_raleigh_incidents():
        """Fetch yesterday's Raleigh police incident records (incremental)."""
        from pricepoint.data.geospatial.police_incidents import (
            fetch_daily_raleigh_police_incidents,
        )

        fetch_daily_raleigh_police_incidents()

    @task()
    def verify_load():
        """Verify that records exist in the staging table."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingRaleighPoliceIncident

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(StagingRaleighPoliceIncident)
            ).scalar()
            if not count:
                msg = "No records found in staging_raleigh_police_incidents after load"
                raise RuntimeError(msg)
            logger.info("Verified %d Raleigh police incident records", count)
        finally:
            session.close()

    fetch_daily_raleigh_incidents() >> verify_load()


raleigh_police_collection()
