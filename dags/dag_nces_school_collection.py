"""DAG: Collect NCES school directory data.

Manual-trigger DAG that downloads NCES public school data from the EDGE
ArcGIS REST API and loads it into the nces_schools table.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="nces_school_collection",
    description="Load NCES public school directory data into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "nces", "schools"],
)
def nces_school_collection():
    @task()
    def fetch_schools():
        """Fetch NCES school data from the EDGE API."""
        from pricepoint.data.geospatial.nces_schools import fetch_nces_schools

        count = fetch_nces_schools()
        logger.info("Loaded %d NCES schools", count)

    @task()
    def verify_load():
        """Verify that records were loaded into the nces_schools table."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import NcesSchool

        session = SessionLocal()
        try:
            count = session.execute(select(func.count()).select_from(NcesSchool)).scalar()
            if not count:
                raise RuntimeError("No records found in nces_schools after load")
            logger.info("Verified %d NCES school records", count)
        finally:
            session.close()

    fetch_schools() >> verify_load()


nces_school_collection()
