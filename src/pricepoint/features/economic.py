"""Economic feature engineering.

Transforms macroeconomic time-series into model-ready features:
current mortgage rate, YoY CPI change, local unemployment rate, etc.
"""

from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# FRED series IDs used for feature extraction
SERIES_IDS: dict[str, str] = {
    "mortgage_rate_30yr": "MORTGAGE30US",
    "mortgage_rate_15yr": "MORTGAGE15US",
    "cpi": "CPIAUCSL",
    "unemployment_rate_us": "UNRATE",
    "housing_starts": "HOUST",
    "case_shiller_index": "CSUSHPISA",
    "consumer_sentiment": "UMCSENT",
}

# Features that also need a year-over-year percentage change
YOY_FEATURES: dict[str, str] = {
    "cpi": "cpi_yoy_pct",
    "case_shiller_index": "case_shiller_yoy_pct",
}

_LATEST_VALUE_SQL = text(
    "SELECT value FROM economic_indicators "
    "WHERE series_id = :series_id AND observation_date <= :ref_date "
    "ORDER BY observation_date DESC LIMIT 1"
)

_YOY_VALUE_SQL = text(
    "SELECT value FROM economic_indicators "
    "WHERE series_id = :series_id AND observation_date <= :yoy_date "
    "ORDER BY observation_date DESC LIMIT 1"
)

_PROPERTY_DATES_SQL = text(
    "SELECT id, sold_date, processed_at FROM redfin_listings"
    " WHERE (:filter_ids = false OR id = ANY(:property_ids))"
)


def _get_property_dates(
    db: Session,
    property_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Fetch property reference dates from redfin_listings.

    The reference date is sold_date if available, otherwise processed_at.
    Returns a DataFrame with columns [property_id, ref_date].
    """
    filter_ids = property_ids is not None
    ids_param = list(property_ids) if property_ids else []

    rows = db.execute(
        _PROPERTY_DATES_SQL,
        {"filter_ids": filter_ids, "property_ids": ids_param},
    ).fetchall()

    records = []
    for row in rows:
        pid = row[0]
        sold = row[1]
        processed = row[2]
        ref = sold if sold is not None else processed
        if ref is not None:
            ref_date = ref.date() if hasattr(ref, "date") else ref
            records.append({"property_id": pid, "ref_date": ref_date})

    return pd.DataFrame(records, columns=["property_id", "ref_date"])


def _lookup_value(
    db: Session,
    series_id: str,
    ref_date: date,
) -> float | None:
    """Get the most recent observation value on or before *ref_date*."""
    row = db.execute(
        _LATEST_VALUE_SQL,
        {"series_id": series_id, "ref_date": ref_date},
    ).fetchone()
    return float(row[0]) if row is not None else None


def _lookup_yoy_value(
    db: Session,
    series_id: str,
    ref_date: date,
) -> float | None:
    """Get the observation value roughly 12 months before *ref_date*."""
    yoy_date = date(ref_date.year - 1, ref_date.month, ref_date.day)
    row = db.execute(
        _YOY_VALUE_SQL,
        {"series_id": series_id, "yoy_date": yoy_date},
    ).fetchone()
    return float(row[0]) if row is not None else None


def _compute_yoy_pct(
    current: float | None,
    previous: float | None,
) -> float | None:
    """Compute year-over-year percentage change."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


def _build_row(
    db: Session,
    property_id: int,
    ref_date: date,
) -> dict:
    """Build a single feature row for one property."""
    row: dict = {"property_id": property_id}

    for feature_name, series_id in SERIES_IDS.items():
        current_val = _lookup_value(db, series_id, ref_date)
        row[feature_name] = current_val

        if feature_name in YOY_FEATURES:
            yoy_col = YOY_FEATURES[feature_name]
            previous_val = _lookup_yoy_value(db, series_id, ref_date)
            row[yoy_col] = _compute_yoy_pct(current_val, previous_val)

    return row


def build_economic_features(
    db: Session,
    *,
    property_ids: list[int] | None = None,
    as_of_date: date | None = None,
) -> pd.DataFrame:
    """Compute economic features for properties.

    For each property, find the most recent economic observation on or before
    the property's reference date (sold_date for sold properties, processed_at
    for current listings).

    If *as_of_date* is provided it overrides per-property dates (useful for
    scoring new listings that have no sold_date yet).

    Parameters
    ----------
    db:
        SQLAlchemy session.
    property_ids:
        Limit to these property IDs.  ``None`` means all.
    as_of_date:
        Override reference date for all properties.

    Returns
    -------
    pd.DataFrame
        Indexed by ``property_id`` with 10 feature columns.
    """
    logger.info("Fetching property reference dates...")
    t0 = time.monotonic()
    prop_dates = _get_property_dates(db, property_ids)
    logger.info("Got %d property dates in %.1fs", len(prop_dates), time.monotonic() - t0)

    if prop_dates.empty:
        cols = ["property_id"] + list(SERIES_IDS.keys()) + list(YOY_FEATURES.values())
        return pd.DataFrame(columns=cols).set_index("property_id")

    if as_of_date is not None:
        prop_dates["ref_date"] = as_of_date

    num_properties = len(prop_dates)
    num_queries = num_properties * (len(SERIES_IDS) + len(YOY_FEATURES))
    logger.info(
        "Building economic features for %d properties (%d series + %d YoY = ~%d DB lookups)...",
        num_properties,
        len(SERIES_IDS),
        len(YOY_FEATURES),
        num_queries,
    )

    t0 = time.monotonic()
    rows: list[dict] = []
    log_interval = max(1, num_properties // 10)  # Log every ~10%
    for i, (_, r) in enumerate(prop_dates.iterrows()):
        rows.append(_build_row(db, int(r["property_id"]), r["ref_date"]))
        if (i + 1) % log_interval == 0 or (i + 1) == num_properties:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (num_properties - i - 1) / rate if rate > 0 else 0
            logger.info(
                "  Economic features: %d/%d properties (%.1f/s, ~%.0fs remaining)",
                i + 1,
                num_properties,
                rate,
                remaining,
            )

    df = pd.DataFrame(rows)
    logger.info(
        "Economic features built in %.1fs (%.1f properties/s)",
        time.monotonic() - t0,
        num_properties / (time.monotonic() - t0) if (time.monotonic() - t0) > 0 else 0,
    )
    return df.set_index("property_id")


def build_training_economic_features(
    db: Session,
    sale_events: pd.DataFrame,
) -> pd.DataFrame:
    """Compute economic features for each historical sale event.

    Instead of looking up indicators as-of the property's most recent
    ``sold_date``, this function uses each sale event's individual date.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    sale_events:
        DataFrame with columns ``sale_event_id``, ``property_id``,
        ``sale_date``.  Typically produced by
        :func:`~pricepoint.features.housing.build_training_sale_events`.

    Returns
    -------
    pd.DataFrame
        Indexed by ``sale_event_id`` with economic feature columns.
    """
    if sale_events.empty:
        cols = ["sale_event_id"] + list(SERIES_IDS.keys()) + list(YOY_FEATURES.values())
        return pd.DataFrame(columns=cols).set_index("sale_event_id")

    num_events = len(sale_events)
    num_queries = num_events * (len(SERIES_IDS) + len(YOY_FEATURES))
    logger.info(
        "Building training economic features for %d sale events (~%d DB lookups)...",
        num_events,
        num_queries,
    )

    t0 = time.monotonic()
    rows: list[dict] = []
    log_interval = max(1, num_events // 10)

    for i, (_, r) in enumerate(sale_events.iterrows()):
        sale_event_id = r["sale_event_id"]
        ref_date = r["sale_date"]
        if hasattr(ref_date, "date"):
            ref_date = ref_date.date()

        row = _build_row(db, int(r["property_id"]), ref_date)
        # Replace property_id key with sale_event_id
        row.pop("property_id", None)
        row["sale_event_id"] = sale_event_id
        rows.append(row)

        if (i + 1) % log_interval == 0 or (i + 1) == num_events:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (num_events - i - 1) / rate if rate > 0 else 0
            logger.info(
                "  Training economic features: %d/%d events (%.1f/s, ~%.0fs remaining)",
                i + 1,
                num_events,
                rate,
                remaining,
            )

    df = pd.DataFrame(rows)
    logger.info(
        "Training economic features built in %.1fs",
        time.monotonic() - t0,
    )
    return df.set_index("sale_event_id")
