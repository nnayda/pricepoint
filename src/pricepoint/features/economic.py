"""Economic feature engineering.

Transforms macroeconomic time-series into model-ready features:
current mortgage rate, YoY CPI change, local unemployment rate, etc.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

# FRED series IDs used for feature extraction
SERIES_IDS: dict[str, str] = {
    "mortgage_rate_30yr": "MORTGAGE30US",
    "mortgage_rate_15yr": "MORTGAGE15US",
    "cpi": "CPIAUCSL",
    "unemployment_rate_us": "UNRATE",
    "unemployment_rate_nc": "NCUR",
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
    prop_dates = _get_property_dates(db, property_ids)

    if prop_dates.empty:
        cols = ["property_id"] + list(SERIES_IDS.keys()) + list(YOY_FEATURES.values())
        return pd.DataFrame(columns=cols).set_index("property_id")

    if as_of_date is not None:
        prop_dates["ref_date"] = as_of_date

    rows = [_build_row(db, int(r["property_id"]), r["ref_date"]) for _, r in prop_dates.iterrows()]

    df = pd.DataFrame(rows)
    return df.set_index("property_id")
