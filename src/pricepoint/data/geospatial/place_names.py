"""Refresh the place_names lookup table from the places table.

Uses a staging-table approach with chunked inserts and an atomic swap
to avoid OOM, minimize WAL pressure, and keep the live table available
throughout the rebuild.
"""

import logging
import string

from sqlalchemy import text

from pricepoint.db import SessionLocal

logger = logging.getLogger(__name__)

# Characters used to partition name inserts into manageable chunks.
_CHUNK_KEYS: list[str] = list(string.ascii_lowercase) + list(string.digits)


def _create_staging_table() -> None:
    """Drop any previous staging table and create a fresh unlogged one."""
    with SessionLocal() as session:
        session.execute(
            text("""
                DROP TABLE IF EXISTS place_names_staging;
                CREATE UNLOGGED TABLE place_names_staging (
                    id SERIAL PRIMARY KEY,
                    match_type VARCHAR NOT NULL,
                    value VARCHAR NOT NULL,
                    category VARCHAR,
                    count INTEGER NOT NULL,
                    refreshed_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
        )
        session.commit()
    logger.info("Created unlogged staging table place_names_staging")


def _insert_brands() -> int:
    """Insert brand aggregates into the staging table. Returns row count."""
    with SessionLocal() as session:
        result = session.execute(
            text("""
                INSERT INTO place_names_staging
                    (match_type, value, category, count, refreshed_at)
                SELECT 'brand', brand_name, MIN(category), COUNT(*), NOW()
                FROM places
                WHERE brand_name IS NOT NULL
                GROUP BY brand_name
            """)
        )
        session.commit()
        row_count = result.rowcount  # type: ignore[attr-defined]
    logger.info("Inserted %d brand rows into staging", row_count)
    return row_count


def _add_unique_constraint() -> None:
    """Add a unique constraint on (match_type, value) for ON CONFLICT support."""
    with SessionLocal() as session:
        session.execute(
            text("""
                ALTER TABLE place_names_staging
                ADD CONSTRAINT uq_place_names_staging_type_value
                UNIQUE (match_type, value)
            """)
        )
        session.commit()
    logger.info("Added unique constraint on staging table")


def _insert_names_chunk(chunk_key: str | None) -> int:
    """Insert one chunk of name aggregates.

    *chunk_key* is a single lowercase letter or digit.  ``None`` means
    "everything that doesn't start with a-z or 0-9".
    """
    if chunk_key is not None:
        where_clause = "AND LOWER(LEFT(p.name, 1)) = :key"
        params = {"key": chunk_key}
        label = chunk_key
    else:
        where_clause = "AND p.name !~ '^[a-zA-Z0-9]'"
        params = {}
        label = "other"

    sql = f"""
        INSERT INTO place_names_staging
            (match_type, value, category, count, refreshed_at)
        SELECT 'name', p.name, MIN(p.category), COUNT(*), NOW()
        FROM places p
        LEFT JOIN place_names_staging pn
            ON pn.value = p.name AND pn.match_type = 'brand'
        WHERE p.name IS NOT NULL
          AND pn.value IS NULL
          {where_clause}
        GROUP BY p.name
        ON CONFLICT (match_type, value) DO NOTHING
    """

    with SessionLocal() as session:
        result = session.execute(text(sql), params)
        session.commit()
        row_count = result.rowcount  # type: ignore[attr-defined]
    logger.info("Chunk '%s': inserted %d name rows", label, row_count)
    return row_count


def _build_trigram_index() -> None:
    """Build the GIN trigram index on the staging table."""
    with SessionLocal() as session:
        session.execute(
            text("""
                CREATE INDEX ix_place_names_staging_value_trgm
                ON place_names_staging USING gin (value gin_trgm_ops)
            """)
        )
        session.commit()
    logger.info("Built GIN trigram index on staging table")


def _atomic_swap() -> None:
    """Rename staging → live in a single transaction (transactional DDL)."""
    with SessionLocal() as session:
        session.execute(
            text("""
                DROP TABLE IF EXISTS place_names_old;
                ALTER TABLE place_names RENAME TO place_names_old;
                DROP TABLE place_names_old;
                ALTER TABLE place_names_staging RENAME TO place_names;
                ALTER TABLE place_names
                    RENAME CONSTRAINT uq_place_names_staging_type_value
                    TO uq_place_name_type_value;
                ALTER INDEX ix_place_names_staging_value_trgm
                    RENAME TO ix_place_names_value_trgm;
            """)
        )
        session.commit()
    logger.info("Atomic swap complete — staging is now live")


def refresh_place_names() -> None:
    """Rebuild place_names from the current places table.

    1. Create an unlogged staging table (fast inserts, no WAL).
    2. Insert brand aggregates (single query — small result set).
    3. Add a unique constraint for ON CONFLICT safety.
    4. Insert name aggregates in ~37 chunks (a-z, 0-9, other).
    5. Build a GIN trigram index on the staging table.
    6. Atomically swap staging → live so the table is never empty.
    """
    logger.info("Starting place_names refresh (chunked staging approach)")

    _create_staging_table()
    _insert_brands()
    _add_unique_constraint()

    total_names = 0
    for key in _CHUNK_KEYS:
        total_names += _insert_names_chunk(key)
    # Catch names starting with non-alphanumeric characters.
    total_names += _insert_names_chunk(None)
    logger.info("Inserted %d total name rows across all chunks", total_names)

    _build_trigram_index()
    _atomic_swap()

    logger.info("place_names refresh complete")
