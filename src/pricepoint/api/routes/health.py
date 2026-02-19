"""Health and readiness check endpoints."""

from fastapi import APIRouter, Request

from pricepoint.api.rate_limit import limiter
from pricepoint.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
@limiter.limit(get_settings().rate_limit_default)
async def health(request: Request) -> dict:
    """Liveness probe — returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    """Readiness probe — returns 200 if the service can accept traffic.

    In production this would check database connectivity, model availability, etc.
    """
    return {"status": "ready"}
