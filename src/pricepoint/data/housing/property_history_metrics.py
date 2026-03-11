"""Build rolling market metrics by township and month.

Aggregates sold Redfin listings joined to property_geo_lookups to produce
avg days on market, median sale price, and sample counts at 1-month,
3-month, and 1-year rolling windows.
"""

import logging
from collections import defaultdict
from datetime import date, datetime
from statistics import median
from typing import NamedTuple

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pricepoint.db.models import PropertyGeoLookup, PropertyHistoryMetric, RedfinListing

logger = logging.getLogger(__name__)

MIN_SAMPLE_SIZE = 5


def _has_new_sold_listings(session: Session) -> bool:
    """Check if any SOLD listings were processed after the latest metric build."""
    latest_built = session.scalar(select(func.max(PropertyHistoryMetric.built_at)))
    if latest_built is None:
        return True  # No metrics built yet — need a full build
    new_count = session.scalar(
        select(func.count(RedfinListing.id)).where(
            RedfinListing.listing_status == "SOLD",
            RedfinListing.processed_at > latest_built,
        )
    )
    return (new_count or 0) > 0


class SaleRecord(NamedTuple):
    """Minimal sale record for metric computation."""

    sold_date: date
    sold_price: float
    days_on_market: int


def _fetch_sale_records(session: Session) -> dict[str, list[SaleRecord]]:
    """Fetch sold listings with township geoid, grouped by township."""
    rows = (
        session.query(
            PropertyGeoLookup.county_subdivision_geoid,
            RedfinListing.sold_date,
            RedfinListing.sold_price,
            RedfinListing.contract_date,
        )
        .join(RedfinListing, RedfinListing.id == PropertyGeoLookup.property_id)
        .filter(
            RedfinListing.sold_date.isnot(None),
            RedfinListing.contract_date.isnot(None),
            RedfinListing.sold_price.isnot(None),
            PropertyGeoLookup.county_subdivision_geoid.isnot(None),
        )
        .all()
    )

    by_township: dict[str, list[SaleRecord]] = defaultdict(list)
    for geoid, sold_date, sold_price, contract_date in rows:
        if isinstance(sold_date, datetime):
            sold_date = sold_date.date()
        if isinstance(contract_date, datetime):
            contract_date = contract_date.date()
        dom = (sold_date - contract_date).days
        if dom < 0:
            continue
        by_township[geoid].append(SaleRecord(sold_date, sold_price, dom))

    return dict(by_township)


def _month_range(min_date: date, max_date: date) -> list[date]:
    """Generate first-of-month dates from min_date's month through max_date's month."""
    start = date(min_date.year, min_date.month, 1)
    end = date(max_date.year, max_date.month, 1)
    months: list[date] = []
    current = start
    while current <= end:
        months.append(current)
        current += relativedelta(months=1)
    return months


def _compute_window(
    sales: list[SaleRecord],
    window_start: date,
    window_end: date,
) -> tuple[float | None, float | None, int]:
    """Compute avg DOM and median price for sales in [window_start, window_end)."""
    subset = [s for s in sales if window_start <= s.sold_date < window_end]
    count = len(subset)
    if count < MIN_SAMPLE_SIZE:
        return None, None, count
    avg_dom = sum(s.days_on_market for s in subset) / count
    med_price = median(s.sold_price for s in subset)
    return round(avg_dom, 2), round(med_price, 2), count


def build_property_history_metrics(
    session: Session,
    *,
    force_rebuild: bool = False,
) -> int:
    """Build property_history_metrics table from sold Redfin listings.

    When ``force_rebuild`` is False (default), short-circuits if no new
    SOLD listings have been processed since the last metric build.

    Returns the number of metric rows upserted.
    """
    if not force_rebuild and not _has_new_sold_listings(session):
        logger.info("No new SOLD listings since last build; skipping history metrics")
        return 0

    by_township = _fetch_sale_records(session)
    if not by_township:
        logger.warning("No sold listings with township geoid found — nothing to build")
        return 0

    logger.info("Building history metrics for %d townships", len(by_township))

    today = date.today()
    current_month = date(today.year, today.month, 1)

    rows_to_insert: list[PropertyHistoryMetric] = []

    for geoid, sales in by_township.items():
        min_sold = min(s.sold_date for s in sales)
        months = _month_range(min_sold, today)

        for month in months:
            if month >= current_month:
                continue

            w1_start = month - relativedelta(months=1)
            w3_start = month - relativedelta(months=3)
            w12_start = month - relativedelta(months=12)

            avg_dom_1m, med_price_1m, cnt_1m = _compute_window(sales, w1_start, month)
            avg_dom_3m, med_price_3m, cnt_3m = _compute_window(sales, w3_start, month)
            avg_dom_1y, med_price_1y, cnt_1y = _compute_window(sales, w12_start, month)

            rows_to_insert.append(
                PropertyHistoryMetric(
                    township_geoid=geoid,
                    metric_month=month,
                    avg_days_on_market_1m=avg_dom_1m,
                    avg_days_on_market_3m=avg_dom_3m,
                    avg_days_on_market_1y=avg_dom_1y,
                    median_sale_price_1m=med_price_1m,
                    median_sale_price_3m=med_price_3m,
                    median_sale_price_1y=med_price_1y,
                    sample_count_1m=cnt_1m,
                    sample_count_3m=cnt_3m,
                    sample_count_1y=cnt_1y,
                )
            )

    # Delete-and-reinsert (full rebuild each run)
    session.execute(delete(PropertyHistoryMetric))
    session.add_all(rows_to_insert)
    session.flush()

    logger.info("Built %d property history metric rows", len(rows_to_insert))
    return len(rows_to_insert)


def verify_property_history_metrics(session: Session) -> dict[str, int]:
    """Verify property_history_metrics table has data.

    Returns summary stats and raises if the table is empty.
    """
    total = session.query(PropertyHistoryMetric).count()
    townships = session.query(PropertyHistoryMetric.township_geoid).distinct().count()
    with_1m = (
        session.query(PropertyHistoryMetric)
        .filter(PropertyHistoryMetric.avg_days_on_market_1m.isnot(None))
        .count()
    )

    stats = {"total_rows": total, "townships": townships, "rows_with_1m_data": with_1m}
    logger.info("Property history metrics verification: %s", stats)

    if total == 0:
        raise RuntimeError("property_history_metrics table is empty after build")

    return stats
