"""LLM-based property photo quality scoring.

Uses a local Ollama instance with a vision model to rate property photos on a
0-100 scale. Pure parsing functions are stateless; I/O functions handle HTTP,
S3, and DB interactions.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.data.housing.description_scorer import (
    extract_json_from_text,
)
from pricepoint.db.engine import SessionLocal
from pricepoint.db.models import LlmPhotoScore, RedfinListing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for photo quality scoring
# ---------------------------------------------------------------------------
PHOTO_SYSTEM_PROMPT = """\
You are a Virtual Home Inspector and Real Estate Photographer Analyst. Your \
goal is to objectively evaluate the material condition, design quality, and \
renovation level of a property based SOLELY on its listing photos.

SCORING PHILOSOPHY:
- Start at a baseline of 50 (Standard, livable, average home).
- Add points ONLY for visible high-value features (e.g., stone countertops, \
hardwood floors, modern fixtures, professional landscaping, new appliances).
- Subtract points for visible defects, dated finishes, clutter, or poor \
maintenance.
- Ignore photo staging quality — focus on the actual property condition.

SCORING GUIDELINES (0-100):

90-100: Ultra-Luxury / Flawless
Visible high-end finishes throughout (marble, custom cabinetry, designer \
fixtures). Professional-grade kitchen, spa-like bathrooms, smart home features, \
pristine condition. No visible flaws.

75-89: Premium / Fully Renovated
High-end finishes visible (quartz/granite, hardwood, stainless appliances). \
Cohesive modern design, well-maintained exterior, updated mechanicals evident.

60-74: Above Average / Partial Updates
Generally good condition. Some rooms updated (kitchen or bath), but others \
may show older finishes. Clean, well-maintained, standard desirable features.

45-59: Average / Standard Builder Grade
Functional and livable but uninspired. Laminate counters, basic fixtures, \
carpet in living areas, standard white appliances. Typical starter home.

30-44: Below Average / Dated
Visually obsolete. Popcorn ceilings, wood paneling, dated tile, old carpet, \
brass fixtures. Clean but needs cosmetic modernization.

15-29: Poor / Deferred Maintenance
Visible neglect: peeling paint, stained surfaces, damaged flooring, overgrown \
exterior. Significant work needed before move-in.

0-14: Distressed / Uninhabitable
Structural damage visible, missing fixtures, mold, fire damage, incomplete \
construction, or severe deterioration.

VISUAL PRIORITY LIST (what to look for):
1. **Kitchen:** Countertop material, appliance brand/age, cabinet condition
2. **Bathrooms:** Fixtures, tile, vanity quality, cleanliness
3. **Flooring:** Hardwood vs carpet vs laminate vs tile; condition
4. **Walls/Ceilings:** Paint condition, crown molding, popcorn ceilings
5. **Exterior:** Roof condition, siding, landscaping, curb appeal
6. **Windows/Doors:** Age, style, condition
7. **Overall:** Clutter, staging, natural light, room sizes

DETECTED FEATURES — identify visible features in these categories:
- kitchen_features: countertop material, appliance brands, island, backsplash
- bathroom_features: fixtures, tile, double vanity, shower type
- flooring: hardwood, carpet, tile, laminate
- exterior_features: roof, siding, landscaping, garage, pool
- special_features: fireplace, built-ins, smart home, wine cellar, etc.

RESPONSE FORMAT — respond with ONLY this JSON object:
{
  "visual_quality_score": <integer 0-100>,
  "visual_reasoning": "<1-3 sentences. Be direct. Cite specific visible \
features that justified the score.>",
  "detected_features": {
    "kitchen_features": ["<feature>", ...],
    "bathroom_features": ["<feature>", ...],
    "flooring": ["<feature>", ...],
    "exterior_features": ["<feature>", ...],
    "special_features": ["<feature>", ...]
  },
  "renovation_level": "<one of: new_construction, fully_renovated, \
partially_updated, original_maintained, original_dated, needs_work, distressed>"
}

RULES:
1. Base assessment ONLY on the photos provided.
2. If photos are unclear, low quality, or insufficient, return null for all \
fields.
3. Be strict. A standard home is a 50, not a 75.
4. Do not assume features you cannot see."""

PHOTO_USER_PROMPT = "Analyze these property listing photos."


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def compute_photos_hash(photo_keys: list[str]) -> str:
    """Return SHA-256 hex digest of sorted photo S3 keys.

    Hashes the S3 paths (not content) for performance. Sorting ensures
    order-independence.
    """
    joined = "\n".join(sorted(photo_keys))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compute_prompt_version() -> str:
    """Return a short hash of the scoring prompts.

    Changes to the system or user prompt produce a new version string,
    enabling re-scoring with updated prompts while keeping history.
    """
    combined = build_system_prompt() + "\n" + build_user_prompt()
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:12]


def build_system_prompt() -> str:
    """Return the system prompt for photo quality scoring."""
    return PHOTO_SYSTEM_PROMPT


def build_user_prompt() -> str:
    """Return the user prompt for photo analysis."""
    return PHOTO_USER_PROMPT


def parse_llm_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate the LLM vision response fields.

    Returns a dict with visual_quality_score, visual_reasoning,
    detected_features, renovation_level — all potentially None if
    photos were insufficient.
    """
    score = raw.get("visual_quality_score")
    reasoning = raw.get("visual_reasoning")
    features = raw.get("detected_features")
    renovation = raw.get("renovation_level")

    # All-null check (insufficient photos)
    if score is None and reasoning is None and features is None and renovation is None:
        return {
            "visual_quality_score": None,
            "visual_reasoning": None,
            "detected_features": None,
            "renovation_level": None,
        }

    # Validate score: must be int 0-100, clamp if out of range
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        score = int(score)
        score = max(0, min(100, score))
    else:
        score = None

    # Validate reasoning
    if not isinstance(reasoning, str):
        reasoning = None

    # Validate detected_features: must be a dict
    if not isinstance(features, dict):
        features = {}

    # Validate renovation_level: must be a string
    if not isinstance(renovation, str):
        renovation = None

    return {
        "visual_quality_score": score,
        "visual_reasoning": reasoning,
        "detected_features": features,
        "renovation_level": renovation,
    }


# ---------------------------------------------------------------------------
# S3 helper
# ---------------------------------------------------------------------------


def download_photos_as_base64(
    photo_keys: list[str],
    *,
    s3_client: Any | None = None,
) -> list[str]:
    """Download photos from S3 and return as base64-encoded strings.

    Creates a boto3 client from settings if not injected. Skips individual
    failed downloads with a warning.
    """
    if not photo_keys:
        return []

    settings = get_settings()

    if s3_client is None:
        import boto3

        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    bucket = settings.s3_bucket
    images: list[str] = []

    failures = 0
    for key in photo_keys:
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            encoded = base64.b64encode(body).decode("utf-8")
            images.append(encoded)
        except Exception:
            failures += 1
            logger.warning("Failed to download photo from S3: %s/%s", bucket, key)

    if failures:
        logger.warning(
            "S3 download: %d/%d photos failed for batch",
            failures,
            len(photo_keys),
        )

    return images


# ---------------------------------------------------------------------------
# Async I/O
# ---------------------------------------------------------------------------


async def call_ollama_vision(
    images: list[str],
    *,
    client: httpx.AsyncClient | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    """Call Ollama chat API to score property listing photos.

    Accepts multiple base64-encoded images in a single request (multi-image
    models like Gemma 3). Returns parsed JSON dict or None on failure.
    """
    settings = get_settings()
    base_url = base_url or settings.ollama_base_url
    model = model or settings.ollama_vision_model
    timeout = timeout or settings.ollama_timeout_seconds

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(), "images": images},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
        },
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout)
        should_close = True

    try:
        response = await client.post(f"{base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        text = data.get("message", {}).get("content", "")
        parsed = extract_json_from_text(text)
        if parsed is None:
            # Log full response metadata for diagnosis (exclude message content
            # which is already shown, and avoid logging huge fields)
            diag = {k: v for k, v in data.items() if k not in ("message", "context")}
            logger.warning(
                "Ollama vision returned unparseable response (len=%d): %.300s "
                "| response_meta=%s | image_sizes=%s",
                len(text),
                text,
                diag,
                [len(img) for img in images],
            )
        return parsed
    except httpx.TimeoutException:
        logger.warning(
            "Ollama vision request timed out (limit=%ds, %d images)", timeout, len(images)
        )
        return None
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response else ""
        logger.warning("Ollama vision HTTP error %s: %s", exc.response.status_code, body)
        return None
    except Exception:
        logger.exception("Unexpected error calling Ollama vision")
        return None
    finally:
        if should_close:
            await client.aclose()


async def score_photos_batch(
    listings: list[dict[str, Any]],
    model_name: str,
    model_version: str,
    *,
    existing_hashes: dict[tuple[int, str, str], str] | None = None,
    ollama_fn: Callable[..., Any] | None = None,
    s3_fn: Callable[..., Any] | None = None,
    max_concurrent: int = 1,
) -> list[dict[str, Any]]:
    """Score a batch of listings' photos concurrently.

    Each item in listings must have keys: id, property_photos (list of S3 keys).
    existing_hashes maps (listing_id, model_name, model_version) -> photos_hash
    for skipping unchanged photo sets.

    Returns list of result dicts ready for DB insert.
    """
    existing_hashes = existing_hashes or {}
    ollama_fn = ollama_fn or call_ollama_vision
    s3_fn = s3_fn or download_photos_as_base64

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[dict[str, Any]] = []

    async def _score_one(listing: dict[str, Any]) -> dict[str, Any] | None:
        listing_id = listing["id"]
        photo_keys = listing.get("property_photos") or []

        if not photo_keys:
            return None

        photos_hash = compute_photos_hash(photo_keys)

        # Skip if same hash already exists
        existing = existing_hashes.get((listing_id, model_name, model_version))
        if existing == photos_hash:
            return None

        # Download photos from S3
        images = s3_fn(photo_keys)
        if not images:
            logger.warning(
                "Listing %d: no photos downloaded from S3 (%d keys attempted)",
                listing_id,
                len(photo_keys),
            )
            return None

        # Score all photos in a single multi-image request
        async with semaphore:
            raw = await ollama_fn(images)

        if raw is None:
            logger.warning(
                "Listing %d: Ollama scoring failed (%d photos)",
                listing_id,
                len(images),
            )
            return {
                "listing_id": listing_id,
                "model_name": model_name,
                "model_version": model_version,
                "photos_hash": photos_hash,
                "visual_quality_score": None,
                "visual_reasoning": None,
                "detected_features": None,
                "renovation_level": None,
                "raw_response": {"error": "ollama_call_failed"},
            }

        parsed = parse_llm_response(raw)
        return {
            "listing_id": listing_id,
            "model_name": model_name,
            "model_version": model_version,
            "photos_hash": photos_hash,
            "visual_quality_score": parsed["visual_quality_score"],
            "visual_reasoning": parsed["visual_reasoning"],
            "detected_features": parsed["detected_features"],
            "renovation_level": parsed["renovation_level"],
            "raw_response": raw,
        }

    tasks = [_score_one(listing) for listing in listings]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for idx, r in enumerate(batch_results):
        if isinstance(r, BaseException):
            listing_id = listings[idx].get("id", "unknown")
            logger.error(
                "Listing %s: photo scoring raised %s: %s",
                listing_id,
                type(r).__name__,
                r,
            )
        elif isinstance(r, dict):
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Sync entry point (called from Airflow)
# ---------------------------------------------------------------------------


def _score_single_listing(
    listing: dict[str, Any],
    model_name: str,
    model_version: str,
    existing_hashes: dict[tuple[int, str, str], str],
    ollama_fn: Callable[..., Any],
    s3_fn: Callable[..., Any],
) -> dict[str, Any] | None:
    """Score a single listing's photos synchronously.

    Returns a result dict ready for DB insert, or None if skipped.
    """
    listing_id = listing["id"]
    photo_keys = listing.get("property_photos") or []

    if not photo_keys:
        return None

    photos_hash = compute_photos_hash(photo_keys)

    # Skip if same hash already exists
    existing = existing_hashes.get((listing_id, model_name, model_version))
    if existing == photos_hash:
        return None

    # Download photos from S3
    images = s3_fn(photo_keys)
    if not images:
        logger.warning(
            "Listing %d: no photos downloaded from S3 (%d keys attempted)",
            listing_id,
            len(photo_keys),
        )
        return None

    # Score all photos in a single multi-image request
    raw = asyncio.run(ollama_fn(images))

    if raw is None:
        logger.warning(
            "Listing %d: Ollama scoring failed (%d photos)",
            listing_id,
            len(images),
        )
        return {
            "listing_id": listing_id,
            "model_name": model_name,
            "model_version": model_version,
            "photos_hash": photos_hash,
            "visual_quality_score": None,
            "visual_reasoning": None,
            "detected_features": None,
            "renovation_level": None,
            "raw_response": {"error": "ollama_call_failed"},
        }

    parsed = parse_llm_response(raw)
    return {
        "listing_id": listing_id,
        "model_name": model_name,
        "model_version": model_version,
        "photos_hash": photos_hash,
        "visual_quality_score": parsed["visual_quality_score"],
        "visual_reasoning": parsed["visual_reasoning"],
        "detected_features": parsed["detected_features"],
        "renovation_level": parsed["renovation_level"],
        "raw_response": raw,
    }


def score_all_photos(
    log_interval: int = 50,
    *,
    ollama_fn: Callable[..., Any] | None = None,
    s3_fn: Callable[..., Any] | None = None,
) -> dict[str, int]:
    """Score all Redfin listing photos that need scoring.

    Each listing is scored and committed individually so progress is
    never lost on failure.

    Returns dict with keys: scored, skipped, errors.
    """
    settings = get_settings()
    model_name = settings.ollama_vision_model
    model_version = compute_prompt_version()
    ollama_fn = ollama_fn or call_ollama_vision
    s3_fn = s3_fn or download_photos_as_base64

    session = SessionLocal()
    try:
        # Load existing hashes for this model
        existing_rows = session.execute(
            select(
                LlmPhotoScore.listing_id,
                LlmPhotoScore.model_name,
                LlmPhotoScore.model_version,
                LlmPhotoScore.photos_hash,
            ).where(
                LlmPhotoScore.model_name == model_name,
                LlmPhotoScore.model_version == model_version,
            )
        ).all()

        existing_hashes: dict[tuple[int, str, str], str] = {
            (row.listing_id, row.model_name, row.model_version): row.photos_hash
            for row in existing_rows
        }

        # Load listings with photos
        all_listings = session.execute(
            select(RedfinListing.id, RedfinListing.property_photos).where(
                RedfinListing.property_photos.isnot(None)
            )
        ).all()

        listings = [{"id": row.id, "property_photos": row.property_photos} for row in all_listings]

        total_listings = len(listings)
        total_photos = sum(len(lt.get("property_photos") or []) for lt in listings)
        scored = 0
        skipped = 0
        errors = 0

        logger.info(
            "Photo scoring started: %d listings (%d total photos), model=%s/%s",
            total_listings,
            total_photos,
            model_name,
            model_version,
        )

        run_start = time.monotonic()

        for idx, listing in enumerate(listings, start=1):
            try:
                result = _score_single_listing(
                    listing,
                    model_name,
                    model_version,
                    existing_hashes,
                    ollama_fn,
                    s3_fn,
                )
            except Exception:
                logger.exception("Listing %s: unexpected error during scoring", listing["id"])
                errors += 1
                continue

            if result is None:
                skipped += 1
                continue

            if result["raw_response"].get("error"):
                errors += 1
                continue

            # Upsert and commit immediately
            stmt = pg_insert(LlmPhotoScore).values(result)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_llm_photo_score_listing_model",
                set_={
                    "photos_hash": stmt.excluded.photos_hash,
                    "visual_quality_score": stmt.excluded.visual_quality_score,
                    "visual_reasoning": stmt.excluded.visual_reasoning,
                    "detected_features": stmt.excluded.detected_features,
                    "renovation_level": stmt.excluded.renovation_level,
                    "raw_response": stmt.excluded.raw_response,
                    "extracted_at": func.now(),
                },
            )
            session.execute(stmt)

            session.commit()
            key = (result["listing_id"], result["model_name"], result["model_version"])
            existing_hashes[key] = result["photos_hash"]
            scored += 1

            # Progress logging
            if idx % log_interval == 0 or idx == total_listings:
                total_elapsed = time.monotonic() - run_start
                if idx < total_listings:
                    avg_per_listing = total_elapsed / idx
                    remaining = (total_listings - idx) * avg_per_listing
                    eta_min, eta_sec = divmod(int(remaining), 60)
                    eta_str = f"{eta_min}m{eta_sec:02d}s"
                else:
                    eta_str = "done"

                logger.info(
                    "Progress: %d/%d listings (%.0f%%) | "
                    "%d scored, %d skipped, %d errors | ETA: %s",
                    idx,
                    total_listings,
                    idx / total_listings * 100,
                    scored,
                    skipped,
                    errors,
                    eta_str,
                )

        total_elapsed = time.monotonic() - run_start
        elapsed_min, elapsed_sec = divmod(int(total_elapsed), 60)

        logger.info(
            "Photo scoring complete: %d scored, %d skipped, %d errors "
            "in %dm%02ds (%d listings, %d photos)",
            scored,
            skipped,
            errors,
            elapsed_min,
            elapsed_sec,
            total_listings,
            total_photos,
        )
        return {"scored": scored, "skipped": skipped, "errors": errors}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_photo_scores() -> None:
    """Verify photo scores exist in the database.

    Raises RuntimeError if the llm_photo_scores table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(LlmPhotoScore)).scalar()
        if not count:
            raise RuntimeError("No records found in llm_photo_scores after scoring")
        logger.info("Verified %d records in llm_photo_scores", count)
    finally:
        session.close()
