"""Health and readiness check endpoints."""

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.rate_limit import limiter
from pricepoint.config.settings import get_settings
from pricepoint.db.models import LlmPhotoScore, RedfinListing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Simple TTL cache for stats
_stats_cache: dict[str, Any] = {"ts": 0.0}
_STATS_TTL = 300  # 5 minutes
_DATA_SOURCE_COUNT = 8


@router.get("/health")
@limiter.limit(get_settings().rate_limit_default)
async def health(request: Request) -> dict:
    """Liveness probe — returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    """Readiness probe — checks database connectivity.

    Returns 200 if the database is reachable, 503 otherwise.
    """
    try:
        db.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ready"}, status_code=200)
    except Exception:
        logger.exception("Readiness check failed: database unreachable")
        return JSONResponse(content={"status": "not_ready"}, status_code=503)


@router.get("/api/stats")
def stats(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return aggregate statistics with a 5-minute TTL cache."""
    now = time.monotonic()
    if now - _stats_cache["ts"] < _STATS_TTL and "listing_count" in _stats_cache:
        return {
            "listing_count": _stats_cache["listing_count"],
            "photos_analyzed": _stats_cache["photos_analyzed"],
            "data_source_count": _stats_cache["data_source_count"],
        }

    listing_count = db.execute(select(func.count(RedfinListing.id))).scalar() or 0
    photos_analyzed = db.execute(select(func.count(LlmPhotoScore.id))).scalar() or 0

    _stats_cache["listing_count"] = listing_count
    _stats_cache["photos_analyzed"] = photos_analyzed
    _stats_cache["data_source_count"] = _DATA_SOURCE_COUNT
    _stats_cache["ts"] = now
    return {
        "listing_count": listing_count,
        "photos_analyzed": photos_analyzed,
        "data_source_count": _DATA_SOURCE_COUNT,
    }
