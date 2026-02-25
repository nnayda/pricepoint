"""DAG: Build gold-layer greenspaces table.

Filters Wake open space bronze data into a deduplicated
``greenspaces`` gold table with type normalisation.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="greenspace_gold_tables",
    description="Build gold greenspaces table from Wake open space bronze data",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "greenspace"],
)
def greenspace_gold_tables():
    @task()
    def build_greenspaces_gold():
        """Build gold greenspaces table from bronze sources."""
        from pricepoint.data.geospatial.greenspace_gold_builder import (
            build_greenspaces_gold as _build,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = _build(session)
            session.commit()
            logger.info("Greenspace gold build stats: %s", stats)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def verify_gold():
        """Verify gold greenspaces table has been populated."""
        from sqlalchemy import func, select

        from pricepoint.db.engine import SessionLocal
        from pricepoint.db.models import Greenspace

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(Greenspace)
            ).scalar()
            if not count:
                raise RuntimeError("No records in gold greenspaces table after build")
            logger.info("Verified gold greenspaces table: %d records", count)
        finally:
            session.close()

    build_greenspaces_gold() >> verify_gold()


greenspace_gold_tables()
