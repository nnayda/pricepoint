"""Health and readiness check endpoints."""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.rate_limit import limiter
from pricepoint.config.settings import get_settings
from pricepoint.db.models import RedfinListing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Simple TTL cache for listing count
_stats_cache: dict[str, float | int] = {"count": 0, "ts": 0.0}
_STATS_TTL = 300  # 5 minutes


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
    """Return aggregate statistics (listing count) with a 5-minute TTL cache."""
    now = time.monotonic()
    if now - _stats_cache["ts"] < _STATS_TTL and _stats_cache["count"]:
        return {"listing_count": int(_stats_cache["count"])}

    count = db.execute(select(func.count(RedfinListing.id))).scalar() or 0
    _stats_cache["count"] = count
    _stats_cache["ts"] = now
    return {"listing_count": count}
