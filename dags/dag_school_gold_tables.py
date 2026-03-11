"""DAG: Build gold-layer school tables.

Auto-triggered DAG that builds the gold ``schools`` and ``property_schools``
tables from NCES reference data and Redfin-extracted school information.
Runs automatically after either the Redfin transform or NCES collection
DAG produces new data.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="school_gold_tables",
    description="Build gold schools and property_schools from NCES + Redfin data",
    schedule=[Asset("redfin_listings"), Asset("nces_schools")],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "schools"],
)
def school_gold_tables():
    @task()
    def build_schools_gold():
        """Build gold schools table from NCES + Redfin data."""
        from pricepoint.data.housing.school_gold_builder import (
            build_schools_gold as _build,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            count = _build(session)
            session.commit()
            logger.info("Built %d gold school records", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def build_property_schools_gold():
        """Build gold property_schools table (incremental).

        Each property is committed individually inside the builder so that
        progress is durable and a single property error doesn't lose work.
        """
        from pricepoint.data.housing.school_gold_builder import (
            build_property_schools_gold as _build,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = _build(session)
            logger.info("Gold property_schools stats: %s", stats)
            if stats.get("errors"):
                raise RuntimeError(f"Completed with {stats['errors']} property errors — check logs")
        finally:
            session.close()

    @task(outlets=[Asset("schools")])
    def verify_gold():
        """Verify gold tables have been populated."""
        from pricepoint.data.housing.school_gold_builder import verify_schools_gold
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            verify_schools_gold(session)
        finally:
            session.close()

    build_schools_gold() >> build_property_schools_gold() >> verify_gold()


school_gold_tables()
