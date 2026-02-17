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
from sqlalchemy import select

from pricepoint.config.settings import get_settings
from pricepoint.data.housing.description_scorer import (
    _get_model_version,
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

    for key in photo_keys:
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            encoded = base64.b64encode(body).decode("utf-8")
            images.append(encoded)
        except Exception:
            logger.warning("Failed to download photo from S3: %s", key)

    return images


# ---------------------------------------------------------------------------
# Async I/O
# ---------------------------------------------------------------------------


def merge_photo_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-photo LLM results into a single listing-level score.

    Takes the median score, concatenates reasoning, unions detected features,
    and picks the most common renovation level.
    """
    scores = [
        r["visual_quality_score"] for r in results if r.get("visual_quality_score") is not None
    ]
    reasonings = [r["visual_reasoning"] for r in results if r.get("visual_reasoning")]
    renovation_levels = [r["renovation_level"] for r in results if r.get("renovation_level")]

    # Merge detected features: union all lists per category
    merged_features: dict[str, list[str]] = {}
    for r in results:
        feats = r.get("detected_features") or {}
        for category, items in feats.items():
            if isinstance(items, list):
                existing = merged_features.setdefault(category, [])
                for item in items:
                    if item not in existing:
                        existing.append(item)

    # Median score
    if scores:
        scores.sort()
        mid = len(scores) // 2
        median_score = scores[mid] if len(scores) % 2 else (scores[mid - 1] + scores[mid]) // 2
    else:
        median_score = None

    # Most common renovation level
    if renovation_levels:
        from collections import Counter

        renovation = Counter(renovation_levels).most_common(1)[0][0]
    else:
        renovation = None

    return {
        "visual_quality_score": median_score,
        "visual_reasoning": " | ".join(reasonings) if reasonings else None,
        "detected_features": merged_features or None,
        "renovation_level": renovation,
    }


async def call_ollama_vision(
    image: str,
    *,
    client: httpx.AsyncClient | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    """Call Ollama vision API to score a single property photo.

    Returns parsed JSON dict or None on failure.
    """
    settings = get_settings()
    base_url = base_url or settings.ollama_base_url
    model = model or settings.ollama_vision_model
    timeout = timeout or settings.ollama_timeout_seconds

    payload = {
        "model": model,
        "system": build_system_prompt(),
        "prompt": build_user_prompt(),
        "images": [image],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024,
        },
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout)
        should_close = True

    try:
        response = await client.post(f"{base_url}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "")
        return extract_json_from_text(text)
    except httpx.TimeoutException:
        logger.warning("Ollama vision request timed out")
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
            logger.warning("No photos downloaded for listing %d", listing_id)
            return None

        # Score each photo individually (model only supports single image)
        per_photo_results: list[dict[str, Any]] = []
        all_raw: list[dict[str, Any] | None] = []
        for img in images:
            async with semaphore:
                raw = await ollama_fn(img)
            all_raw.append(raw)
            if raw is not None:
                per_photo_results.append(parse_llm_response(raw))

        if not per_photo_results:
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

        merged = merge_photo_results(per_photo_results)
        return {
            "listing_id": listing_id,
            "model_name": model_name,
            "model_version": model_version,
            "photos_hash": photos_hash,
            "visual_quality_score": merged["visual_quality_score"],
            "visual_reasoning": merged["visual_reasoning"],
            "detected_features": merged["detected_features"],
            "renovation_level": merged["renovation_level"],
            "raw_response": [r for r in all_raw if r is not None],
        }

    tasks = [_score_one(listing) for listing in listings]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in batch_results:
        if isinstance(r, BaseException):
            logger.error("Photo scoring task failed: %s", r)
        elif isinstance(r, dict):
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Sync entry point (called from Airflow)
# ---------------------------------------------------------------------------


def score_all_photos(
    batch_size: int = 50,
    *,
    ollama_fn: Callable[..., Any] | None = None,
    s3_fn: Callable[..., Any] | None = None,
) -> dict[str, int]:
    """Score all Redfin listing photos that need scoring.

    Returns dict with keys: scored, skipped, errors.
    """
    settings = get_settings()
    model_name = settings.ollama_vision_model
    model_version = _get_model_version(model_name)

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
        total_batches = (total_listings + batch_size - 1) // batch_size
        scored = 0
        skipped = 0
        errors = 0
        photos_processed = 0

        logger.info(
            "Photo scoring started: %d listings (%d total photos), "
            "%d batches (size %d), model=%s/%s",
            total_listings,
            total_photos,
            total_batches,
            batch_size,
            model_name,
            model_version,
        )

        run_start = time.monotonic()

        # Process in batches
        for batch_idx, i in enumerate(range(0, total_listings, batch_size), start=1):
            batch_start = time.monotonic()
            batch = listings[i : i + batch_size]
            batch_photo_count = sum(len(lt.get("property_photos") or []) for lt in batch)

            results = asyncio.run(
                score_photos_batch(
                    batch,
                    model_name,
                    model_version,
                    existing_hashes=existing_hashes,
                    ollama_fn=ollama_fn,
                    s3_fn=s3_fn,
                )
            )

            batch_scored = 0
            batch_errors = 0
            for result in results:
                if result["raw_response"].get("error"):
                    errors += 1
                    batch_errors += 1
                    continue

                # Upsert: check existing then insert/update
                existing = (
                    session.query(LlmPhotoScore)
                    .filter(
                        LlmPhotoScore.listing_id == result["listing_id"],
                        LlmPhotoScore.model_name == result["model_name"],
                        LlmPhotoScore.model_version == result["model_version"],
                    )
                    .first()
                )

                if existing:
                    existing.photos_hash = result["photos_hash"]
                    existing.visual_quality_score = result["visual_quality_score"]
                    existing.visual_reasoning = result["visual_reasoning"]
                    existing.detected_features = result["detected_features"]
                    existing.renovation_level = result["renovation_level"]
                    existing.raw_response = result["raw_response"]
                else:
                    session.add(LlmPhotoScore(**result))

                scored += 1
                batch_scored += 1

            session.commit()

            # Update existing_hashes with newly scored
            for result in results:
                if not result["raw_response"].get("error"):
                    key = (result["listing_id"], result["model_name"], result["model_version"])
                    existing_hashes[key] = result["photos_hash"]

            # Progress logging with ETA
            batch_elapsed = time.monotonic() - batch_start
            total_elapsed = time.monotonic() - run_start
            listings_processed = i + len(batch)
            photos_processed += batch_photo_count
            batch_skipped = len(batch) - batch_scored - batch_errors

            if listings_processed < total_listings:
                avg_per_listing = total_elapsed / listings_processed
                remaining = (total_listings - listings_processed) * avg_per_listing
                eta_min, eta_sec = divmod(int(remaining), 60)
                eta_str = f"{eta_min}m{eta_sec:02d}s"
            else:
                eta_str = "done"

            logger.info(
                "Batch %d/%d complete: %d scored, %d skipped, %d errors "
                "(%d photos, %.1fs) | Total: %d/%d listings (%.0f%%), "
                "%d/%d photos | ETA: %s",
                batch_idx,
                total_batches,
                batch_scored,
                batch_skipped,
                batch_errors,
                batch_photo_count,
                batch_elapsed,
                listings_processed,
                total_listings,
                listings_processed / total_listings * 100,
                photos_processed,
                total_photos,
                eta_str,
            )

        # Calculate skipped (listings with photos minus scored minus errors)
        skipped = total_listings - scored - errors
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
    finally:
        session.close()
