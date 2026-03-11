"""Build gold-layer police_incidents table from staging sources.

Consolidates Raleigh, Cary, and Morrisville staging tables into a single
``police_incidents`` gold table with UCR-standardized crime groups/categories.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr, lookup_ucr
from pricepoint.db.models import (
    PoliceIncident,
    StagingCaryPoliceIncident,
    StagingMorrisvillePoliceIncident,
    StagingRaleighPoliceIncident,
)

logger = logging.getLogger(__name__)

_MINIMUM_EXPECTED_INCIDENTS = 500


def _parse_morrisville_date(date_str: str | None) -> datetime | None:
    """Parse Morrisville date string (MM/DD/YYYY) into a date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y")
    except (ValueError, AttributeError):
        logger.debug("Could not parse Morrisville date: %r", date_str)
        return None


def _upsert_incident(session: Session, incident_id: str, fields: dict) -> None:
    """Insert or update a PoliceIncident by incident_id."""
    existing = session.execute(
        select(PoliceIncident).where(PoliceIncident.incident_id == incident_id)
    ).scalar_one_or_none()

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        session.add(PoliceIncident(incident_id=incident_id, **fields))


def build_police_incidents_gold(session: Session) -> int:
    """Build the gold ``police_incidents`` table from all staging sources.

    Uses UPSERT on ``incident_id`` to keep records stable across rebuilds.
    Does NOT delete stale records (staging only has ~5 years of data).

    Returns the number of gold records created or updated.

    Raises RuntimeError if total staging records < 500.
    """
    raleigh_count = (
        session.scalar(select(func.count()).select_from(StagingRaleighPoliceIncident)) or 0
    )
    cary_count = session.scalar(select(func.count()).select_from(StagingCaryPoliceIncident)) or 0
    morrisville_count = (
        session.scalar(select(func.count()).select_from(StagingMorrisvillePoliceIncident)) or 0
    )
    total_staging = raleigh_count + cary_count + morrisville_count

    if total_staging < _MINIMUM_EXPECTED_INCIDENTS:
        raise RuntimeError(
            f"Only {total_staging} total staging records found, "
            f"expected >= {_MINIMUM_EXPECTED_INCIDENTS}. "
            "Aborting gold build to prevent data loss."
        )

    count = 0
    start_time = time.monotonic()
    last_log_time = start_time

    # --- Raleigh ---
    raleigh_rows = session.execute(select(StagingRaleighPoliceIncident)).scalars().all()
    logger.info("Processing %d Raleigh staging records", len(raleigh_rows))

    for rpd in raleigh_rows:
        incident_id = f"RPD-{rpd.case_number}" if rpd.case_number else f"RPD-{rpd.id}"
        group, category = lookup_ucr(rpd.crime_code)  # type: ignore[arg-type]

        fields: dict = {
            "crime_code": rpd.crime_code,
            "crime_group": group,
            "crime_category": category,
            "crime_description": rpd.crime_description,
            "address": rpd.reported_block_address,
            "date_of_incident": rpd.reported_date.date() if rpd.reported_date else None,
            "latitude": rpd.latitude,
            "longitude": rpd.longitude,
            "location": rpd.location,
        }
        _upsert_incident(session, incident_id, fields)
        count += 1

        now = time.monotonic()
        if now - last_log_time >= 30:
            last_log_time = now
            elapsed = now - start_time
            rate = count / elapsed if elapsed > 0 else 0
            logger.info(
                "Progress: %d/%d (%.0f%%) | %.1f rec/sec",
                count,
                total_staging,
                count / total_staging * 100,
                rate,
            )

    # --- Cary ---
    cary_rows = session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    logger.info("Processing %d Cary staging records", len(cary_rows))

    for cpd in cary_rows:
        incident_id = f"CPD-{cpd.incident_number}" if cpd.incident_number else f"CPD-{cpd.id}"
        group, category = lookup_ucr(cpd.ucr)  # type: ignore[arg-type]

        fields = {
            "crime_code": cpd.ucr,
            "crime_group": group,
            "crime_category": category,
            "crime_description": cpd.crime_type,
            "address": cpd.geocode,
            "date_of_incident": cpd.date_from.date() if cpd.date_from else None,
            "latitude": cpd.lat,
            "longitude": cpd.lon,
            "location": cpd.location,
        }
        _upsert_incident(session, incident_id, fields)
        count += 1

        now = time.monotonic()
        if now - last_log_time >= 30:
            last_log_time = now
            elapsed = now - start_time
            rate = count / elapsed if elapsed > 0 else 0
            logger.info(
                "Progress: %d/%d (%.0f%%) | %.1f rec/sec",
                count,
                total_staging,
                count / total_staging * 100,
                rate,
            )

    # --- Morrisville ---
    morrisville_rows = session.execute(select(StagingMorrisvillePoliceIncident)).scalars().all()
    logger.info("Processing %d Morrisville staging records", len(morrisville_rows))

    for mpd in morrisville_rows:
        incident_id = f"MPD-{mpd.inci_id}" if mpd.inci_id else f"MPD-{mpd.id}"
        matched_code, group, category = fuzzy_match_ucr(mpd.offense)  # type: ignore[arg-type]

        parsed_date = _parse_morrisville_date(mpd.date_occu)  # type: ignore[arg-type]

        fields = {
            "crime_code": matched_code,
            "crime_group": group,
            "crime_category": category,
            "crime_description": mpd.offense,
            "address": mpd.street,
            "date_of_incident": parsed_date.date() if parsed_date else None,
            "latitude": mpd.lat,
            "longitude": mpd.lon,
            "location": mpd.location,
        }
        _upsert_incident(session, incident_id, fields)
        count += 1

        now = time.monotonic()
        if now - last_log_time >= 30:
            last_log_time = now
            elapsed = now - start_time
            rate = count / elapsed if elapsed > 0 else 0
            logger.info(
                "Progress: %d/%d (%.0f%%) | %.1f rec/sec",
                count,
                total_staging,
                count / total_staging * 100,
                rate,
            )

    session.flush()
    elapsed = time.monotonic() - start_time
    logger.info("Built %d gold police incident records in %.1f sec", count, elapsed)
    return count


def verify_police_incidents_gold(session: Session) -> dict[str, int]:
    """Verify the gold police_incidents table has been populated.

    Returns a dict with 'police_incidents' count.
    Raises RuntimeError if the table is empty after build.
    """
    incident_count = session.scalar(select(func.count()).select_from(PoliceIncident)) or 0
    if not incident_count:
        raise RuntimeError("No records in gold police_incidents table after build")
    logger.info("Verified gold police_incidents: %d records", incident_count)
    return {"police_incidents": incident_count}
