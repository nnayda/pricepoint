"""Cache management endpoint — invalidate cached data by prefix."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from pricepoint.api.auth import get_current_user
from pricepoint.api.cache import invalidate_pattern
from pricepoint.api.dependencies import get_valkey
from pricepoint.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cache"])

# Allowed cache prefixes to prevent arbitrary key deletion
ALLOWED_PREFIXES = {"crime", "pois", "greenspace", "utilities", "geocode", "property", "forecast"}


@router.delete("/cache/{prefix}")
async def delete_cache(
    prefix: str,
    _user: Annotated[User, Depends(get_current_user)],
    valkey: Annotated[Redis | None, Depends(get_valkey)] = None,
) -> dict:
    """Invalidate all cached keys with the given prefix.

    Requires authentication.  Returns the number of keys deleted.
    """
    if prefix not in ALLOWED_PREFIXES:
        return {"prefix": prefix, "deleted": 0, "error": f"Unknown prefix: {prefix}"}

    deleted = await invalidate_pattern(valkey, f"{prefix}:*")
    logger.info("Cache invalidation: prefix=%s deleted=%d", prefix, deleted)
    return {"prefix": prefix, "deleted": deleted}
