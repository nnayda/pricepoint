"""Redfin listing HTML collection and reprocessing DAGs.

Daily DAG processes new HTML files from the configured directory.
Manual DAG reprocesses archived files from S3 when parsing logic changes.
"""

import logging
from datetime import datetime

from airflow.sdk import Asset, dag, task
from sqlalchemy import func, select

logger = logging.getLogger(__name__)

STAGING_DATASET = Asset("staging_redfin_listings")


@dag(
    dag_id="redfin_listing_collection",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
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
        logger.info("Processed %d files, %d errors", result["processed"], result["errors"])

    @task(outlets=[STAGING_DATASET])
    def verify_load():
        """Verify at least one record exists in staging table."""
        from pricepoint.db import SessionLocal
        from pricepoint.db.models import StagingRedfinListing

        session = SessionLocal()
        try:
            count = session.execute(select(func.count()).select_from(StagingRedfinListing)).scalar()

            if not count:
                raise RuntimeError("No records found in staging_redfin_listings")

            logger.info("Verification successful: %d records in staging table", count)

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
        "retries": 0,
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
        logger.info("Reprocessed %d files, %d errors", result["processed"], result["errors"])

    reprocess_from_s3()


redfin_listing_reprocess()
