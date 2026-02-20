"""Collect macroeconomic indicators from the FRED API.

Fetches time-series data (mortgage rates, CPI, unemployment, housing starts, etc.)
and stores observations in the ``economic_indicators`` table with incremental
(only-newer) loading and ``ON CONFLICT DO NOTHING`` upsert semantics.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pricepoint.config.settings import get_settings
from pricepoint.db import SessionLocal
from pricepoint.db.models import EconomicIndicator

logger = logging.getLogger(__name__)

try:
    from fredapi import Fred
except ImportError:  # pragma: no cover
    Fred = None  # type: ignore[assignment,misc]


def _get_latest_date(db: Session, series_id: str) -> date | None:
    """Return the most recent observation_date for *series_id*, or ``None``."""
    result = db.execute(
        select(EconomicIndicator.observation_date)
        .where(EconomicIndicator.series_id == series_id)
        .order_by(EconomicIndicator.observation_date.desc())
        .limit(1)
    ).scalar()
    return result


def _fetch_series(
    fred: "Fred",
    series_id: str,
    start_date: date,
) -> list[dict]:
    """Fetch observations for a single FRED series starting from *start_date*.

    Returns a list of dicts with keys ``series_id``, ``observation_date``, ``value``.
    """
    try:
        series = fred.get_series(series_id, observation_start=start_date)
    except Exception:
        logger.exception("Failed to fetch FRED series %s", series_id)
        return []

    rows: list[dict] = []
    for obs_date, value in series.items():
        if value is None or (hasattr(value, "__class__") and str(value) == "."):
            continue
        try:
            float_val = float(value)
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "series_id": series_id,
                "observation_date": obs_date.date() if hasattr(obs_date, "date") else obs_date,
                "value": float_val,
            }
        )
    return rows


def _bulk_upsert(db: Session, rows: list[dict]) -> int:
    """Insert rows into economic_indicators with ON CONFLICT DO NOTHING.

    Returns the number of rows actually inserted.
    """
    if not rows:
        return 0

    stmt = pg_insert(EconomicIndicator).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        constraint="uq_economic_series_date",
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount  # type: ignore[attr-defined,return-value]


def fetch_macro_indicators(db: Session | None = None) -> dict[str, int]:
    """Download macroeconomic time-series data from FRED.

    For each configured series, queries the DB for the latest observation date
    and fetches only newer data. Uses bulk insert with conflict handling.

    Parameters
    ----------
    db:
        Optional SQLAlchemy session. A new session is created (and closed)
        if ``None``.

    Returns
    -------
    dict[str, int]
        Mapping of series_id to the count of newly inserted observations.
    """
    if Fred is None:
        raise ImportError(
            "fredapi is required for economic data collection. Install it with: pip install fredapi"
        )

    settings = get_settings()

    if not settings.fred_api_key:
        raise ValueError("fred_api_key must be set to fetch FRED data")

    fred = Fred(api_key=settings.fred_api_key)
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        fallback_start = date.today() - timedelta(days=365 * settings.fred_lookback_years)
        counts: dict[str, int] = {}

        for series_id in settings.fred_series_ids:
            latest = _get_latest_date(db, series_id)  # type: ignore[arg-type]
            start = (latest + timedelta(days=1)) if latest else fallback_start

            logger.info(
                "Fetching FRED series %s from %s",
                series_id,
                start.isoformat(),
            )
            rows = _fetch_series(fred, series_id, start)
            inserted = _bulk_upsert(db, rows)  # type: ignore[arg-type]
            counts[series_id] = inserted
            logger.info(
                "Series %s: fetched %d observations, inserted %d new",
                series_id,
                len(rows),
                inserted,
            )

        return counts
    except Exception:
        if own_session:
            db.rollback()  # type: ignore[union-attr]
        raise
    finally:
        if own_session:
            db.close()  # type: ignore[union-attr]
