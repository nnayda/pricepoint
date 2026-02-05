"""DAG: Collect Cary police incident data from the Town of Cary Open Data Portal.

Runs weekly to truncate and reload the staging table with all incident records.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="cary_police_collection",
    description="Weekly full refresh of Cary police incident staging data",
    schedule="@weekly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "cary", "police"],
)
def cary_police_collection():
    @task()
    def fetch_cary_incidents():
        """Fetch all Cary police incident records (truncate + reload)."""
        from pricepoint.data.geospatial.police_incidents import fetch_cary_police_incidents

        fetch_cary_police_incidents(full_refresh=True)

    @task()
    def verify_load():
        """Verify that records were loaded into the staging table."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingCaryPoliceIncident

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(StagingCaryPoliceIncident)
            ).scalar()
            if not count:
                raise RuntimeError("No records found in staging_cary_police_incidents after load")
        finally:
            session.close()

    fetch_cary_incidents() >> verify_load()


cary_police_collection()
