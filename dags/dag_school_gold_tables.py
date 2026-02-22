"""DAG: Build gold-layer school tables.

Auto-triggered DAG that builds the gold ``schools`` and ``property_schools``
tables from NCES reference data and Redfin-extracted school information.
Runs automatically after the Redfin transform DAG produces new listings.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="school_gold_tables",
    description="Build gold schools and property_schools from NCES + Redfin data",
    schedule=[Asset("redfin_listings")],
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
        """Build gold property_schools table (incremental)."""
        from pricepoint.data.housing.school_gold_builder import (
            build_property_schools_gold as _build,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = _build(session)
            session.commit()
            logger.info("Gold property_schools stats: %s", stats)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def verify_gold():
        """Verify gold tables have been populated."""
        from sqlalchemy import func, select

        from pricepoint.db.engine import SessionLocal
        from pricepoint.db.models import PropertySchool, School

        session = SessionLocal()
        try:
            school_count = session.execute(select(func.count()).select_from(School)).scalar()
            link_count = session.execute(select(func.count()).select_from(PropertySchool)).scalar()
            if not school_count:
                raise RuntimeError("No records in gold schools table after build")
            logger.info(
                "Verified gold tables: %d schools, %d property_schools",
                school_count,
                link_count,
            )
        finally:
            session.close()

    build_schools_gold() >> build_property_schools_gold() >> verify_gold()


school_gold_tables()
