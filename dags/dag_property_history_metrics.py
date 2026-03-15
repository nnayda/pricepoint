"""DAG: Build property history metrics by township and month.

Asset-triggered DAG that aggregates sold Redfin listings into rolling
market metrics (avg days on market, median sale price) at 1-month,
3-month, and 1-year windows per township.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="property_history_metrics",
    description="Build rolling market metrics by township from sold listings",
    schedule=[Asset("redfin_listings"), Asset("property_geo_lookups")],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    params={"force_rebuild": False},
    tags=["data", "gold", "metrics"],
)
def property_history_metrics():
    @task()
    def build_metrics(**context):
        """Build property history metrics table."""
        from pricepoint.data.housing.property_history_metrics import (
            build_property_history_metrics,
        )
        from pricepoint.db.engine import SessionLocal

        force = context["params"].get("force_rebuild", False)
        session = SessionLocal()
        try:
            count = build_property_history_metrics(session, force_rebuild=force)
            session.commit()
            logger.info("Built %d property history metric rows", count)
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task(outlets=[Asset("property_history")])
    def verify_metrics(count):
        """Verify metrics table was populated."""
        from pricepoint.data.housing.property_history_metrics import (
            verify_property_history_metrics,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = verify_property_history_metrics(session)
            logger.info("Verification stats: %s", stats)
        finally:
            session.close()

    result = build_metrics()
    verify_metrics(result)


property_history_metrics()
