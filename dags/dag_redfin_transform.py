"""Redfin staging-to-production transform DAG.

Triggered by Dataset update from the redfin_listing_collection DAG
when new staging records are loaded.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)

STAGING_DATASET = Asset("staging_redfin_listings")
LISTINGS_DATASET = Asset("redfin_listings")


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
    params={"force_rebuild": False},
    tags=["data", "transform", "housing", "redfin"],
)
def redfin_listing_transform():
    """Transform staging Redfin listings into production redfin_listings table."""

    @task()
    def transform_listings(**context):
        """Run the staging-to-production transformation."""
        from pricepoint.data.housing.redfin_transformer import transform_all_listings

        force = context["params"].get("force_rebuild", False)
        result = transform_all_listings(force_rebuild=force)
        logger.info(
            "Transform complete: %d transformed, %d skipped, %d errors",
            result["transformed"],
            result["skipped"],
            result["errors"],
        )
        return result

    @task(outlets=[LISTINGS_DATASET])
    def verify_transform(result):
        """Verify at least one production record exists."""
        from sqlalchemy import func, select

        from pricepoint.db import SessionLocal
        from pricepoint.db.models import RedfinListing

        session = SessionLocal()
        try:
            count = session.execute(select(func.count()).select_from(RedfinListing)).scalar()

            if not count:
                raise RuntimeError("No records found in redfin_listings after transform")

            logger.info("Verification successful: %d records in redfin_listings", count)
        finally:
            session.close()

    result = transform_listings()
    verify_transform(result)


redfin_listing_transform()
