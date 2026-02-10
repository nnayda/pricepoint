"""Redfin staging-to-production transform DAG.

Triggered by Dataset update from the redfin_listing_collection DAG
when new staging records are loaded.
"""

from datetime import datetime, timedelta

from airflow.datasets import Dataset
from airflow.decorators import dag, task
from sqlalchemy import func, select

STAGING_DATASET = Dataset("staging_redfin_listings")


@dag(
    dag_id="redfin_listing_transform",
    schedule=[STAGING_DATASET],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "transform", "housing", "redfin"],
)
def redfin_listing_transform():
    """Transform staging Redfin listings into production property tables."""

    @task()
    def transform_listings():
        """Run the staging-to-production transformation."""
        from pricepoint.data.housing.redfin_transformer import transform_all_listings

        result = transform_all_listings()
        print(
            f"Transform complete: {result['transformed']} transformed, "
            f"{result['skipped']} skipped, {result['errors']} errors"
        )
        return result

    @task()
    def verify_transform(result):
        """Verify at least one production record exists."""
        from pricepoint.db import SessionLocal
        from pricepoint.db.models import PropertyDetail

        session = SessionLocal()
        try:
            count = session.execute(select(func.count()).select_from(PropertyDetail)).scalar()

            if not count:
                raise RuntimeError("No records found in property_details after transform")

            print(f"Verification successful: {count} records in property_details")
        finally:
            session.close()

    result = transform_listings()
    verify_transform(result)


redfin_listing_transform()
