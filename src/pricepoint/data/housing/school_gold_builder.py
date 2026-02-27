"""Build gold-layer school tables from NCES + Redfin bronze data.

Populates the ``schools`` (gold) and ``property_schools`` (gold) tables by
combining authoritative NCES reference data with Redfin-extracted ratings
and school assignments.

Uses UPSERT for stable school IDs and incremental processing for
property-school links (only dirty/new properties are reprocessed).
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from difflib import SequenceMatcher

from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from geoalchemy2.types import Geography
from sqlalchemy import cast, delete, func, or_, select
from sqlalchemy.orm import Session

from pricepoint.data.housing.school_enrichment import (
    _normalize_school_name,
    get_travel_times_batch,
)
from pricepoint.db.models import (
    NcesSchool,
    PropertySchool,
    RedfinListing,
    RedfinPropertySchool,
    RedfinSchool,
    School,
    SchoolDistrict,
)

logger = logging.getLogger(__name__)

# Minimum NCES record count required before rebuilding gold tables.
# Prevents catastrophic purge if NCES collection failed or is mid-refresh.
_MINIMUM_EXPECTED_SCHOOLS = 100

# Meters per mile for ST_DWithin conversion
_METERS_PER_MILE = 1609.344


def _to_wkt_element(location: object) -> WKTElement:
    """Convert a GeoAlchemy2 WKBElement to a WKTElement for use as a bind parameter.

    PostGIS ``ST_GeogFromText`` expects WKT, but WKBElements produce WKB hex
    strings, causing parse errors when cast to ``Geography``.
    """
    shape = to_shape(location)  # type: ignore[arg-type]
    return WKTElement(shape.wkt, srid=4326)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _build_grades_string(nces: NcesSchool) -> str | None:
    """Combine grades_low / grades_high into a display string like 'PK-5'."""
    low = nces.grades_low
    high = nces.grades_high
    if not low and not high:
        return None
    if low and high:
        return f"{low}-{high}" if low != high else low
    return low or high


def _extract_nces_extras(extras: dict | None) -> dict:
    """Parse NCES extras JSON into typed fields.

    Returns dict with keys: enrollment, teachers, student_teacher_ratio,
    free_lunch_eligible, reduced_lunch_eligible, total_frl_eligible.
    """
    if not extras:
        return {}

    result: dict = {}

    def _int(key: str) -> int | None:
        val = extras.get(key)
        if val is None:
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    def _float(key: str) -> float | None:
        val = extras.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    result["enrollment"] = _int("MEMBER")
    result["teachers"] = _float("FTE")
    result["student_teacher_ratio"] = _float("STUTERATIO")
    result["free_lunch_eligible"] = _int("FRELCH")
    result["reduced_lunch_eligible"] = _int("REDLCH")
    result["total_frl_eligible"] = _int("TOTFRL")

    return result


def _find_district_id(session: Session, location: object) -> int | None:
    """Spatial join: find school district containing the given point."""
    if location is None:
        return None

    result = session.execute(
        select(SchoolDistrict.id).where(func.ST_Contains(SchoolDistrict.geom, location))
    ).scalar_one_or_none()

    return result


def _match_redfin_rating(
    session: Session,
    nces_name: str,
    all_redfin_schools: list[RedfinSchool],
) -> float | None:
    """Fuzzy match NCES school name against RedfinSchools to get a rating.

    RedfinSchools have no location, so matching is purely name-based.
    Uses a 0.6 threshold (higher than spatial-assisted) to reduce false positives.
    """
    if not all_redfin_schools:
        return None

    normalized_target = _normalize_school_name(nces_name)
    best_match: RedfinSchool | None = None
    best_score = 0.0

    for candidate in all_redfin_schools:
        normalized_candidate = _normalize_school_name(candidate.name)  # type: ignore[arg-type]
        score = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= 0.6 and best_match is not None:
        return best_match.rating  # type: ignore[return-value]
    return None


def _match_redfin_to_gold(
    redfin_school: RedfinSchool,
    gold_candidates: list[School],
) -> School | None:
    """Fuzzy match a RedfinSchool to a gold School record.

    Callers should pre-filter ``gold_candidates`` by proximity to the property
    (e.g. schools within 15 miles) when the property has a location. When the
    property has no location, pass the full gold school list — matching still
    works, just without spatial narrowing.
    """
    if not gold_candidates:
        return None

    normalized_target = _normalize_school_name(redfin_school.name)  # type: ignore[arg-type]
    best_match: School | None = None
    best_score = 0.0

    for gold in gold_candidates:
        normalized_candidate = _normalize_school_name(gold.name)  # type: ignore[arg-type]
        score = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
        if score > best_score:
            best_score = score
            best_match = gold

    if best_score >= 0.5:
        return best_match
    return None


def _get_nearby_gold_schools(
    session: Session,
    location: object,
    gold_schools: list[School],
    radius_miles: float = 15.0,
) -> list[School]:
    """Filter gold schools to those within radius_miles of a location.

    If location is None, returns the full list (no spatial filtering).
    """
    if location is None:
        return gold_schools

    # Convert WKBElement to WKTElement so PostGIS uses ST_GeomFromText
    # instead of failing with ST_GeogFromText on WKB hex data
    loc_wkt = _to_wkt_element(location)

    radius_m = radius_miles * _METERS_PER_MILE
    nearby_ids: set[int] = set()
    rows = (
        session.execute(
            select(School.id).where(
                School.location.isnot(None),
                func.ST_DWithin(
                    cast(School.location, Geography),
                    cast(loc_wkt, Geography),
                    radius_m,
                ),
            )
        )
        .scalars()
        .all()
    )
    nearby_ids = set(rows)  # type: ignore[arg-type]

    return [gs for gs in gold_schools if gs.id in nearby_ids]


# ---------------------------------------------------------------------------
# Gold builders
# ---------------------------------------------------------------------------


def build_schools_gold(session: Session) -> int:
    """Build the gold ``schools`` table from NCES + Redfin data.

    Uses UPSERT by nces_id to keep School.id stable across rebuilds.
    Returns the number of gold school records created or updated.

    Raises RuntimeError if there are fewer than _MINIMUM_EXPECTED_SCHOOLS
    NCES records, which likely indicates a failed or partial collection.
    """
    nces_count = session.scalar(select(func.count()).select_from(NcesSchool))
    if (nces_count or 0) < _MINIMUM_EXPECTED_SCHOOLS:
        raise RuntimeError(
            f"Only {nces_count} NCES records found, expected >= {_MINIMUM_EXPECTED_SCHOOLS}. "
            "Aborting gold build to prevent data loss — check NCES collection."
        )

    nces_records = session.execute(select(NcesSchool)).scalars().all()
    all_redfin_schools = session.execute(select(RedfinSchool)).scalars().all()

    seen_nces_ids: set[str] = set()
    count = 0
    total_nces = len(nces_records)
    nces_start = time.monotonic()
    nces_last_log = nces_start

    logger.info("Building gold schools from %d NCES records", total_nces)

    for nces in nces_records:
        extras = _extract_nces_extras(nces.extras)  # type: ignore[arg-type]
        grades = _build_grades_string(nces)

        # Compute pct_frl_eligible
        enrollment = extras.get("enrollment")
        total_frl = extras.get("total_frl_eligible")
        pct_frl: float | None = None
        if enrollment and total_frl and enrollment > 0:
            pct_frl = round(total_frl / enrollment * 100, 1)

        # Spatial join for district
        district_id = _find_district_id(session, nces.location)

        # Fuzzy match for Redfin rating (name-only, no spatial filter)
        rating = _match_redfin_rating(
            session,
            nces.name,
            list(all_redfin_schools),  # type: ignore[arg-type]
        )

        seen_nces_ids.add(nces.nces_id)

        # UPSERT: find existing school by nces_id, update or insert
        existing = session.execute(
            select(School).where(School.nces_id == nces.nces_id)
        ).scalar_one_or_none()

        if existing:
            existing.name = nces.name
            existing.street = nces.street
            existing.city = nces.city
            existing.state = nces.state
            existing.zip_code = nces.zip_code
            existing.school_type = nces.school_type
            existing.school_level = nces.school_level
            existing.grades = grades  # type: ignore[assignment]
            existing.rating = rating  # type: ignore[assignment]
            existing.location = nces.location
            existing.enrollment = enrollment  # type: ignore[assignment]
            existing.teachers = extras.get("teachers")  # type: ignore[assignment]
            existing.student_teacher_ratio = extras.get("student_teacher_ratio")  # type: ignore[assignment]
            existing.free_lunch_eligible = extras.get("free_lunch_eligible")  # type: ignore[assignment]
            existing.reduced_lunch_eligible = extras.get("reduced_lunch_eligible")  # type: ignore[assignment]
            existing.total_frl_eligible = total_frl  # type: ignore[assignment]
            existing.pct_frl_eligible = pct_frl  # type: ignore[assignment]
            existing.district_id = district_id  # type: ignore[assignment]
        else:
            session.add(
                School(
                    nces_id=nces.nces_id,
                    name=nces.name,
                    street=nces.street,
                    city=nces.city,
                    state=nces.state,
                    zip_code=nces.zip_code,
                    school_type=nces.school_type,
                    school_level=nces.school_level,
                    grades=grades,
                    rating=rating,
                    location=nces.location,
                    enrollment=enrollment,
                    teachers=extras.get("teachers"),
                    student_teacher_ratio=extras.get("student_teacher_ratio"),
                    free_lunch_eligible=extras.get("free_lunch_eligible"),
                    reduced_lunch_eligible=extras.get("reduced_lunch_eligible"),
                    total_frl_eligible=total_frl,
                    pct_frl_eligible=pct_frl,
                    district_id=district_id,
                )
            )
        count += 1

        now = time.monotonic()
        if now - nces_last_log >= 30 or count == total_nces:
            nces_last_log = now
            elapsed = now - nces_start
            rate = count / elapsed if elapsed > 0 else 0
            remaining = (total_nces - count) / rate if rate > 0 else 0
            logger.info(
                "Schools progress: %d/%d (%.0f%%) | %.1f schools/sec | ETA: %.1f min",
                count,
                total_nces,
                count / total_nces * 100,
                rate,
                remaining / 60,
            )

    # Remove schools whose NCES records no longer exist (school closures)
    # The minimum-count guard above ensures seen_nces_ids is never empty here.
    stale_schools = (
        session.execute(select(School).where(School.nces_id.notin_(seen_nces_ids))).scalars().all()
    )
    for stale in stale_schools:
        # Cascade-delete their PropertySchool links
        session.execute(delete(PropertySchool).where(PropertySchool.school_id == stale.id))
        session.delete(stale)
        logger.info("Removed stale gold school: %s (nces_id=%s)", stale.name, stale.nces_id)

    session.flush()
    logger.info("Built %d gold school records (upsert)", count)
    return count


def _get_dirty_properties(session: Session) -> list[RedfinListing]:
    """Find properties that need gold school rebuilding.

    A property is "dirty" if:
    - It has a location (required for school matching)
    - AND: schools_built_at is NULL (never built) OR
      schools_built_at < processed_at (re-transformed)
    """
    return list(
        session.execute(
            select(RedfinListing).where(
                RedfinListing.location.isnot(None),
                or_(
                    RedfinListing.schools_built_at.is_(None),
                    RedfinListing.schools_built_at < RedfinListing.processed_at,
                ),
            )
        )
        .scalars()
        .all()
    )


def build_property_schools_gold(session: Session) -> dict[str, int]:
    """Build the gold ``property_schools`` table incrementally.

    Only processes dirty properties (new or re-transformed since last gold build).
    Uses OSRM Table API for batch travel times instead of per-pair route calls.

    Returns stats dict with 'assigned', 'district', 'total', 'skipped', 'errors' counts.
    """
    # Load all gold schools for matching
    gold_schools = session.execute(select(School)).scalars().all()
    gold_by_district: dict[int, list[School]] = {}
    for gs in gold_schools:
        if gs.district_id is not None:
            gold_by_district.setdefault(gs.district_id, []).append(gs)  # type: ignore[arg-type]

    stats = {"assigned": 0, "district": 0, "total": 0, "skipped": 0, "errors": 0}

    # Only process dirty properties
    dirty_listings = _get_dirty_properties(session)
    all_count = session.execute(
        select(func.count()).select_from(RedfinListing).where(RedfinListing.location.isnot(None))
    ).scalar()
    stats["skipped"] = (all_count or 0) - len(dirty_listings)

    if not dirty_listings:
        logger.info("No dirty properties found — skipping property_schools build")
        return stats

    logger.info(
        "Processing %d dirty properties (%d skipped, already up-to-date)",
        len(dirty_listings),
        stats["skipped"],
    )

    start_time = time.monotonic()
    total_dirty = len(dirty_listings)
    last_log_time = start_time

    for idx, prop in enumerate(dirty_listings, 1):
        try:
            prop_point = to_shape(prop.location)  # type: ignore[arg-type]
            prop_lat, prop_lon = prop_point.y, prop_point.x

            # Convert WKBElement to WKTElement for use as bind parameter
            prop_wkt = _to_wkt_element(prop.location)

            # Delete existing links for this property (rebuild them)
            session.execute(delete(PropertySchool).where(PropertySchool.property_id == prop.id))

            linked_gold_ids: set[int] = set()

            # Pre-filter gold schools by proximity to the property (15 mi)
            nearby_gold = _get_nearby_gold_schools(session, prop.location, list(gold_schools))

            # 1. Match Redfin-assigned schools
            redfin_links = (
                session.execute(
                    select(RedfinPropertySchool).where(RedfinPropertySchool.property_id == prop.id)
                )
                .scalars()
                .all()
            )

            assigned_pairs: list[tuple[School, bool]] = []
            for link in redfin_links:
                redfin_school = session.get(RedfinSchool, link.redfin_school_id)
                if not redfin_school:
                    continue

                gold_match = _match_redfin_to_gold(redfin_school, nearby_gold)
                if gold_match and gold_match.id not in linked_gold_ids:
                    assigned_pairs.append((gold_match, True))
                    linked_gold_ids.add(gold_match.id)  # type: ignore[arg-type]
                    stats["assigned"] += 1

            # 2. Add district schools not already linked
            district_ids = (
                session.execute(
                    select(SchoolDistrict.id).where(func.ST_Contains(SchoolDistrict.geom, prop_wkt))
                )
                .scalars()
                .all()
            )

            district_pairs: list[tuple[School, bool]] = []
            for did in district_ids:
                for gs in gold_by_district.get(did, []):
                    if gs.id in linked_gold_ids:
                        continue
                    district_pairs.append((gs, False))
                    linked_gold_ids.add(gs.id)  # type: ignore[arg-type]
                    stats["district"] += 1

            # 3. Batch compute travel times via OSRM Table API
            all_pairs = assigned_pairs + district_pairs
            schools_with_location = [
                (i, s) for i, (s, _) in enumerate(all_pairs) if s.location is not None
            ]
            dest_coords = [
                (to_shape(s.location).y, to_shape(s.location).x)  # type: ignore[arg-type]
                for _, s in schools_with_location
            ]

            # Compute distances via PostGIS (single query for all schools)
            distances_miles: dict[int, float] = {}
            if schools_with_location:
                school_ids_for_dist = [s.id for _, s in schools_with_location]
                dist_rows = session.execute(
                    select(
                        School.id,
                        func.ST_Distance(
                            cast(School.location, Geography),
                            cast(prop_wkt, Geography),
                        ).label("dist_m"),
                    ).where(School.id.in_(school_ids_for_dist))
                ).all()
                dist_by_school_id = {row.id: row.dist_m for row in dist_rows}
                for pair_idx, school in schools_with_location:
                    dist_m = dist_by_school_id.get(school.id)
                    if dist_m is not None:
                        distances_miles[pair_idx] = round(dist_m / _METERS_PER_MILE, 1)

            # OSRM calls: car + foot in parallel (independent HTTP requests)
            with ThreadPoolExecutor(max_workers=2) as pool:
                car_future = pool.submit(
                    get_travel_times_batch, prop_lat, prop_lon, dest_coords, profile="car"
                )
                foot_future = pool.submit(
                    get_travel_times_batch, prop_lat, prop_lon, dest_coords, profile="walking"
                )
                car_times = car_future.result()
                foot_times = foot_future.result()

            # Map batch results back to school indices
            drive_map: dict[int, int | None] = {}
            walk_map: dict[int, int | None] = {}
            for batch_idx, (pair_idx, _school) in enumerate(schools_with_location):
                car_dur = (
                    car_times[batch_idx]["duration_minutes"] if batch_idx < len(car_times) else None
                )
                foot_dur = (
                    foot_times[batch_idx]["duration_minutes"]
                    if batch_idx < len(foot_times)
                    else None
                )
                drive_map[pair_idx] = int(round(car_dur)) if car_dur is not None else None
                walk_map[pair_idx] = int(round(foot_dur)) if foot_dur is not None else None

            # If schools have locations but OSRM returned no travel times at all,
            # leave the property dirty so it can be reprocessed later.
            if (
                schools_with_location
                and not any(v is not None for v in drive_map.values())
                and not any(v is not None for v in walk_map.values())
            ):
                session.rollback()
                stats["errors"] += 1
                logger.warning(
                    "OSRM returned no travel times for property %s — leaving dirty for retry",
                    prop.id,
                )
                continue

            # Create PropertySchool records
            for i, (school, assigned) in enumerate(all_pairs):
                session.add(
                    PropertySchool(
                        property_id=prop.id,
                        school_id=school.id,
                        assigned=assigned,
                        distance_miles=distances_miles.get(i),
                        drive_minutes=drive_map.get(i),
                        walk_minutes=walk_map.get(i),
                    )
                )

            stats["total"] += len(all_pairs)

            # Stamp schools_built_at so this property won't be reprocessed
            prop.schools_built_at = datetime.now(UTC)  # type: ignore[assignment]

            # Commit per-property so progress is durable
            session.commit()

            now = time.monotonic()
            if now - last_log_time >= 30 or idx == total_dirty:
                last_log_time = now
                elapsed = now - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining = (total_dirty - idx) / rate if rate > 0 else 0
                logger.info(
                    "Progress: %d/%d properties (%.0f%%) | %.1f props/sec | ETA: %.1f min",
                    idx,
                    total_dirty,
                    idx / total_dirty * 100,
                    rate,
                    remaining / 60,
                )

        except Exception:
            session.rollback()
            logger.error("Error building gold schools for property %s", prop.id, exc_info=True)
            stats["errors"] += 1
    logger.info(
        "Built gold property_schools: %d assigned, %d district, %d total, %d skipped, %d errors",
        stats["assigned"],
        stats["district"],
        stats["total"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


def verify_schools_gold(session: Session) -> dict[str, int]:
    """Verify gold school tables have been populated.

    Returns a dict with 'schools' and 'property_schools' counts.
    Raises RuntimeError if the schools table is empty.
    """
    school_count = session.scalar(select(func.count()).select_from(School)) or 0
    link_count = session.scalar(select(func.count()).select_from(PropertySchool)) or 0
    if not school_count:
        raise RuntimeError("No records in gold schools table after build")
    logger.info(
        "Verified gold tables: %d schools, %d property_schools",
        school_count,
        link_count,
    )
    return {"schools": school_count, "property_schools": link_count}
