"""LLM-based property quality scoring from listing descriptions.

Uses a local Ollama instance to rate each property's overall quality on a 0-100
scale. Pure parsing functions are stateless; I/O functions handle HTTP and DB.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pricepoint.config.settings import get_settings
from pricepoint.db.engine import SessionLocal
from pricepoint.db.models import LlmQualityScore, RedfinListing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for quality scoring
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a Skeptical Senior Real Estate Asset Manager. Your goal is to determine \
the objective material condition and luxury level of a property based on its \
listing description. Real estate agents use hyperbole and euphemisms; your job \
is to cut through the marketing fluff to assess the actual asset quality.

SCORING PHILOSOPHY:
- Start at a baseline of 50 (Standard, livable, average home).
- Add points ONLY for explicit high-value features (e.g., "Sub-Zero fridge," \
"new roof 2023," "marble counters").
- Subtract points for euphemisms regarding size, condition, or age.
- Ignore subjective adjectives like "stunning," "gorgeous," or "breathtaking" \
unless supported by specific details.

SCORING GUIDELINES (0-100):

90-100: Ultra-Luxury / Flawless
Truly elite. Specific high-end brands mentioned (Wolf, Sub-Zero), smart home \
integration, heavy structural amenities (elevator, infinity pool), and recent \
professional design. No "builder grade" elements.

75-89: Premium / Fully Renovated
High-end finishes (quartz/granite, hardwood throughout), fully updated \
mechanicals (HVAC, roof), and desirable layout. "Turn-key" with evident pride \
of ownership.

60-74: Above Average / Partial Updates
Generally good condition. Kitchen and primary bath may be updated, but \
secondary rooms might be older. Good bones, clean, standard desirable features \
(fenced yard, garage).

45-59: Average / Standard Builder Grade
Functional and livable but uninspired. Laminate counters, carpet in living \
areas, standard white appliances, or older but well-maintained finishes. \
Typical rental grade or starter home.

30-44: Below Average / Dated
Clean but visually obsolete. Popcorn ceilings, wood paneling, pink/blue \
bathrooms, old carpet. "Time capsule" or "original charm." Livable, but needs \
immediate cosmetic modernization.

15-29: Poor / Deferred Maintenance
"Handyman special," "TLC needed," "Investor special." Evidence of neglect, \
missing flooring, peeling paint, or very old mechanical systems. Cash-only or \
rehab loan likely required.

0-14: Distressed / Uninhabitable
"Tear down," "value in land," "enter at own risk," structural failure, fire \
damage, mold, or incomplete construction.

DECODING AGENT LANGUAGE (Use this dictionary):
- "Cozy" = Small / Cramped
- "Vintage / Retro / Charm" = Old / Outdated systems
- "Great Potential / Blank Canvas" = Needs significant money/work
- "As-Is" = Seller knows there are defects
- "Motivated Seller" = Possible hidden issues or desperation
- "Near transportation" = Potential noise issues (check context)

WHAT TO EVALUATE:
1. **Material Facts:** Focus on nouns (granite, hardwood, roof, HVAC), not \
adjectives (beautiful, amazing).
2. **Age of Systems:** "New roof" is a plus; no mention of roof age in an old \
house is a risk (negative inference).
3. **Kitchen/Bath:** These drive the score. High-end appliances and stone \
counters boost score significantly. Formica/tile drop the score.
4. **Completeness:** Is the renovation finished? "Partially updated" is a \
negative compared to "fully renovated."

RESPONSE FORMAT — respond with ONLY this JSON object:
{
  "quality_score": <integer 0-100>,
  "quality_reasoning": "<1-3 sentences. Be direct and skeptical. Cite specific \
features that justified the score.>",
  "positive_factors": ["<factor 1>", "<factor 2>", ...],
  "negative_factors": ["<factor 1>", "<factor 2>", ...]
}

RULES:
1. Base assessment ONLY on the description.
2. If the description is empty or useless, return null for all fields.
3. Be strict. A standard home is a 50, not a 75.
4. Do not hallucinate features."""


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def compute_description_hash(description: str) -> str:
    """Return SHA-256 hex digest of the description text."""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def build_system_prompt() -> str:
    """Return the system prompt for the quality scoring task."""
    return SYSTEM_PROMPT


def build_user_prompt(description: str) -> str:
    """Wrap description in delimiters for the user prompt."""
    return (
        "Rate the quality of this property based on its listing description:"
        f"\n\n---\n{description}\n---"
    )


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from text using multiple strategies.

    Strategy 1: Direct JSON parse
    Strategy 2: Code fence extraction (```json ... ```)
    Strategy 3: First brace-matched object
    """
    if not text or not text.strip():
        return None

    stripped = text.strip()

    # Strategy 1: direct parse
    try:
        result = json.loads(stripped)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: code fence
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1).strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: brace match
    start = stripped.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(stripped[start : i + 1])
                        if isinstance(result, dict):
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

    # Strategy 4: repair truncated JSON (model hit token limit mid-response)
    if start is not None and start != -1:
        return _repair_truncated_json(stripped[start:])

    return None


def _repair_truncated_json(text: str) -> dict[str, Any] | None:
    """Attempt to repair truncated JSON by closing open brackets/braces.

    When the LLM hits its token limit, the JSON is cut off mid-value.
    Tries closing at the current position first, then progressively
    truncates back to earlier clean break points (commas, closing
    brackets) until a valid parse succeeds.
    """
    if not text or not text.strip():
        return None

    # Collect candidate truncation points: every comma or closing bracket
    # outside a string, plus the full text itself
    candidates: list[int] = [len(text)]
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == '"':
                in_string = False
                candidates.append(i + 1)
        else:
            if ch == '"':
                in_string = True
            elif ch in ",]}":
                candidates.append(i + 1)
        i += 1

    # Try from longest to shortest candidate
    for end in reversed(candidates):
        result = _try_close_json(text[:end])
        if result is not None:
            return result

    return None


def _try_close_json(fragment: str) -> dict[str, Any] | None:
    """Try to close a JSON fragment by appending missing brackets/braces."""
    fragment = fragment.rstrip().rstrip(",")
    if not fragment:
        return None

    # Walk to determine string state and open structures
    in_string = False
    stack: list[str] = []
    i = 0
    while i < len(fragment):
        ch = fragment[i]
        if in_string:
            if ch == "\\" and i + 1 < len(fragment):
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch in "}]" and stack and stack[-1] == ch:
                stack.pop()
        i += 1

    # Close unclosed string
    suffix = ""
    if in_string:
        suffix += '"'
    suffix += "".join(reversed(stack))

    try:
        result = json.loads(fragment + suffix)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def parse_llm_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate the LLM response fields.

    Returns a dict with quality_score, quality_reasoning, positive_factors,
    negative_factors — all potentially None if description was insufficient.
    """
    score = raw.get("quality_score")
    reasoning = raw.get("quality_reasoning")
    positive = raw.get("positive_factors")
    negative = raw.get("negative_factors")

    # All-null check (insufficient description)
    if score is None and reasoning is None and positive is None and negative is None:
        return {
            "quality_score": None,
            "quality_reasoning": None,
            "positive_factors": None,
            "negative_factors": None,
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

    # Validate factors: must be lists of strings
    if isinstance(positive, list):
        positive = [str(f) for f in positive if isinstance(f, str)]
    else:
        positive = []

    if isinstance(negative, list):
        negative = [str(f) for f in negative if isinstance(f, str)]
    else:
        negative = []

    return {
        "quality_score": score,
        "quality_reasoning": reasoning,
        "positive_factors": positive,
        "negative_factors": negative,
    }


# ---------------------------------------------------------------------------
# Async I/O
# ---------------------------------------------------------------------------


async def call_ollama(
    description: str,
    *,
    client: httpx.AsyncClient | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    """Call Ollama API to score a single description.

    Returns parsed JSON dict or None on failure.
    """
    settings = get_settings()
    base_url = base_url or settings.ollama_base_url
    model = model or settings.ollama_model
    timeout = timeout or settings.ollama_timeout_seconds

    payload = {
        "model": model,
        "system": build_system_prompt(),
        "prompt": build_user_prompt(description),
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
        logger.warning("Ollama request timed out for description (%.50s...)", description[:50])
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Ollama HTTP error %s for description (%.50s...)",
            exc.response.status_code,
            description[:50],
        )
        return None
    except Exception:
        logger.exception("Unexpected error calling Ollama")
        return None
    finally:
        if should_close:
            await client.aclose()


async def score_descriptions_batch(
    listings: list[dict[str, Any]],
    model_name: str,
    model_version: str,
    *,
    existing_hashes: dict[tuple[int, str, str], str] | None = None,
    ollama_fn: Callable[..., Any] | None = None,
    max_concurrent: int | None = None,
) -> list[dict[str, Any]]:
    """Score a batch of listings concurrently.

    Each item in listings must have keys: id, description.
    existing_hashes maps (listing_id, model_name, model_version) -> description_hash
    for skipping unchanged descriptions.

    Returns list of result dicts ready for DB insert.
    """
    settings = get_settings()
    max_concurrent = max_concurrent or settings.ollama_max_concurrent
    existing_hashes = existing_hashes or {}
    ollama_fn = ollama_fn or call_ollama

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[dict[str, Any]] = []

    async def _score_one(listing: dict[str, Any]) -> dict[str, Any] | None:
        listing_id = listing["id"]
        description = listing.get("description") or ""

        if not description.strip():
            return None

        desc_hash = compute_description_hash(description)

        # Skip if same hash already exists
        existing = existing_hashes.get((listing_id, model_name, model_version))
        if existing == desc_hash:
            return None

        async with semaphore:
            raw = await ollama_fn(description)

        if raw is None:
            return {
                "listing_id": listing_id,
                "model_name": model_name,
                "model_version": model_version,
                "description_hash": desc_hash,
                "quality_score": None,
                "quality_reasoning": None,
                "positive_factors": None,
                "negative_factors": None,
                "raw_response": {"error": "ollama_call_failed"},
            }

        parsed = parse_llm_response(raw)
        return {
            "listing_id": listing_id,
            "model_name": model_name,
            "model_version": model_version,
            "description_hash": desc_hash,
            "quality_score": parsed["quality_score"],
            "quality_reasoning": parsed["quality_reasoning"],
            "positive_factors": parsed["positive_factors"],
            "negative_factors": parsed["negative_factors"],
            "raw_response": raw,
        }

    tasks = [_score_one(listing) for listing in listings]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in batch_results:
        if isinstance(r, BaseException):
            logger.error("Scoring task failed: %s", r)
        elif isinstance(r, dict):
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Model version helper
# ---------------------------------------------------------------------------


def _get_model_version(model_name: str, *, base_url: str | None = None) -> str:
    """Query Ollama for model digest and return first 12 chars."""
    settings = get_settings()
    base_url = base_url or settings.ollama_base_url

    try:
        response = httpx.post(
            f"{base_url}/api/show",
            json={"name": model_name},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        digest = data.get("digest", "") or data.get("modelfile_digest", "")
        if not digest:
            # Try modelinfo path
            details = data.get("details", {})
            digest = details.get("digest", "unknown")
        return digest[:12] if digest else "unknown"
    except Exception:
        logger.exception("Failed to get model version for %s", model_name)
        return "unknown"


# ---------------------------------------------------------------------------
# Sync entry point (called from Airflow)
# ---------------------------------------------------------------------------


def score_all_descriptions(
    batch_size: int = 50,
    *,
    ollama_fn: Callable[..., Any] | None = None,
) -> dict[str, int]:
    """Score all Redfin listing descriptions that need scoring.

    Returns dict with keys: scored, skipped, errors.
    """
    settings = get_settings()
    model_name = settings.ollama_model
    model_version = _get_model_version(model_name)

    session = SessionLocal()
    try:
        # Load existing hashes for this model
        existing_rows = session.execute(
            select(
                LlmQualityScore.listing_id,
                LlmQualityScore.model_name,
                LlmQualityScore.model_version,
                LlmQualityScore.description_hash,
            ).where(
                LlmQualityScore.model_name == model_name,
                LlmQualityScore.model_version == model_version,
            )
        ).all()

        existing_hashes: dict[tuple[int, str, str], str] = {
            (row.listing_id, row.model_name, row.model_version): row.description_hash
            for row in existing_rows
        }

        # Load listings with descriptions
        all_listings = session.execute(
            select(RedfinListing.id, RedfinListing.description).where(
                RedfinListing.description.isnot(None)
            )
        ).all()

        listings = [{"id": row.id, "description": row.description} for row in all_listings]

        total_listings = len(listings)
        total_batches = (total_listings + batch_size - 1) // batch_size
        scored = 0
        skipped = 0
        errors = 0

        logger.info(
            "Description scoring started: %d listings, %d batches (size %d), model=%s/%s",
            total_listings,
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
            results = asyncio.run(
                score_descriptions_batch(
                    batch,
                    model_name,
                    model_version,
                    existing_hashes=existing_hashes,
                    ollama_fn=ollama_fn,
                )
            )

            batch_scored = 0
            batch_errors = 0
            for result in results:
                if result["raw_response"].get("error"):
                    errors += 1
                    batch_errors += 1
                    continue

                stmt = pg_insert(LlmQualityScore).values(result)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_llm_score_listing_model",
                    set_={
                        "description_hash": stmt.excluded.description_hash,
                        "quality_score": stmt.excluded.quality_score,
                        "quality_reasoning": stmt.excluded.quality_reasoning,
                        "positive_factors": stmt.excluded.positive_factors,
                        "negative_factors": stmt.excluded.negative_factors,
                        "raw_response": stmt.excluded.raw_response,
                        "extracted_at": func.now(),
                    },
                )
                session.execute(stmt)

                scored += 1
                batch_scored += 1

            session.commit()

            # Update existing_hashes with newly scored
            for result in results:
                if not result["raw_response"].get("error"):
                    key = (result["listing_id"], result["model_name"], result["model_version"])
                    existing_hashes[key] = result["description_hash"]

            # Progress logging with ETA
            batch_elapsed = time.monotonic() - batch_start
            total_elapsed = time.monotonic() - run_start
            processed = i + len(batch)
            batch_skipped = len(batch) - batch_scored - batch_errors

            if processed < total_listings:
                avg_per_listing = total_elapsed / processed
                remaining = (total_listings - processed) * avg_per_listing
                eta_min, eta_sec = divmod(int(remaining), 60)
                eta_str = f"{eta_min}m{eta_sec:02d}s"
            else:
                eta_str = "done"

            logger.info(
                "Batch %d/%d complete: %d scored, %d skipped, %d errors "
                "(%.1fs) | Total: %d/%d (%.0f%%) | ETA: %s",
                batch_idx,
                total_batches,
                batch_scored,
                batch_skipped,
                batch_errors,
                batch_elapsed,
                processed,
                total_listings,
                processed / total_listings * 100,
                eta_str,
            )

        # Calculate skipped (listings with unchanged hashes)
        skipped = total_listings - scored - errors
        total_elapsed = time.monotonic() - run_start
        elapsed_min, elapsed_sec = divmod(int(total_elapsed), 60)

        logger.info(
            "Description scoring complete: %d scored, %d skipped, %d errors "
            "in %dm%02ds (%d total listings)",
            scored,
            skipped,
            errors,
            elapsed_min,
            elapsed_sec,
            total_listings,
        )
        return {"scored": scored, "skipped": skipped, "errors": errors}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_description_scores() -> None:
    """Verify description scores exist in the database.

    Raises RuntimeError if the llm_quality_scores table is empty.
    """
    session = SessionLocal()
    try:
        count = session.execute(select(func.count()).select_from(LlmQualityScore)).scalar()
        if not count:
            raise RuntimeError("No records found in llm_quality_scores after scoring")
        logger.info("Verified %d records in llm_quality_scores", count)
    finally:
        session.close()
