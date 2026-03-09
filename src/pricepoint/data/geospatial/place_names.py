"""Refresh the place_names lookup table from the places table.

Truncate-and-rebuild: delete all rows, then re-aggregate brands and names
from places. Callable from Airflow or standalone.
"""

import logging

from sqlalchemy import text

from pricepoint.db import SessionLocal

logger = logging.getLogger(__name__)


def refresh_place_names() -> None:
    """Rebuild place_names from the current places table."""
    with SessionLocal() as session:
        session.execute(text("SET LOCAL work_mem = '256MB'"))
        session.execute(text("TRUNCATE place_names RESTART IDENTITY"))

        brand_result = session.execute(
            text(
                """
                INSERT INTO place_names (match_type, value, category, count, refreshed_at)
                SELECT 'brand', brand_name, MIN(category), COUNT(*), NOW()
                FROM places
                WHERE brand_name IS NOT NULL
                GROUP BY brand_name
                """
            )
        )
        logger.info("Inserted %d brand rows into place_names", brand_result.rowcount)

        name_result = session.execute(
            text(
                """
                INSERT INTO place_names (match_type, value, category, count, refreshed_at)
                SELECT 'name', p.name, MIN(p.category), COUNT(*), NOW()
                FROM places p
                LEFT JOIN place_names pn ON pn.value = p.name AND pn.match_type = 'brand'
                WHERE p.name IS NOT NULL
                  AND pn.value IS NULL
                GROUP BY p.name
                """
            )
        )
        logger.info("Inserted %d name rows into place_names", name_result.rowcount)

        session.commit()
        logger.info("place_names refresh complete")
