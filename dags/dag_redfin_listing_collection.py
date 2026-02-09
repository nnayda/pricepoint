"""Redfin listing HTML collection and reprocessing DAGs.

Daily DAG processes new HTML files from the configured directory.
Manual DAG reprocesses archived files from S3 when parsing logic changes.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from sqlalchemy import func, select


@dag(
    dag_id="redfin_listing_collection",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "housing", "redfin"],
)
def redfin_listing_collection():
    """Process new Redfin HTML listing snapshots (daily schedule)."""

    @task()
    def process_listings_task():
        """Parse HTML files, extract data, upload photos, archive to S3."""
        from pricepoint.data.housing.redfin_listings import process_listings

        result = process_listings()
        print(f"Processed {result['processed']} files, {result['errors']} errors")

    @task()
    def verify_load():
        """Verify at least one record exists in staging table."""
        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingRedfinListing

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(StagingRedfinListing)
            ).scalar()

            if not count:
                raise RuntimeError("No records found in staging_redfin_listings")

            print(f"Verification successful: {count} records in staging table")

        finally:
            session.close()

    process_listings_task() >> verify_load()


redfin_listing_collection()


@dag(
    dag_id="redfin_listing_reprocess",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["data", "collection", "housing", "redfin", "reprocess"],
)
def redfin_listing_reprocess():
    """Reprocess archived Redfin HTML files from S3 (manual trigger)."""

    @task()
    def reprocess_from_s3():
        """Download archived HTML from S3 and re-parse with updated logic."""
        from pricepoint.config.settings import get_settings
        from pricepoint.data.housing.redfin_listings import process_listings

        settings = get_settings()
        result = process_listings(
            reprocess_s3_prefix=settings.redfin_s3_archive_prefix,
        )
        print(f"Reprocessed {result['processed']} files, {result['errors']} errors")

    reprocess_from_s3()


redfin_listing_reprocess()
