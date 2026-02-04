"""Health and readiness check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    """Readiness probe — returns 200 if the service can accept traffic.

    In production this would check database connectivity, model availability, etc.
    """
    return {"status": "ready"}
