"""Health and readiness check endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.rate_limit import limiter
from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


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
