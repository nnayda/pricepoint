"""Unified caching utilities for Valkey (Redis-compatible) cache layer.

Provides helper functions for deterministic key generation, serialization,
deserialization, and pattern-based invalidation.  All functions handle a
``None`` Valkey client gracefully (no-op / return ``None``).
"""

import hashlib
import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def cache_key(prefix: str, **params: Any) -> str:
    """Build a deterministic cache key from a prefix and keyword parameters.

    Parameters are sorted by key name so ordering never affects the digest.
    The resulting key has the form ``prefix:<md5hex>``.
    """
    canonical = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
    raw = f"{prefix}:{canonical}"
    digest = hashlib.md5(raw.encode()).hexdigest()  # noqa: S324
    return f"{prefix}:{digest}"


async def async_cache_get(valkey: Redis | None, key: str) -> dict | None:
    """Fetch and deserialize a cached JSON value.

    Returns ``None`` when *valkey* is ``None``, the key does not exist, or
    deserialization fails.
    """
    if valkey is None:
        return None
    try:
        raw = await valkey.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.warning("Valkey read failed for key %s", key, exc_info=True)
        return None


async def async_cache_set(
    valkey: Redis | None,
    key: str,
    data: dict | list,
    ttl: int,
) -> None:
    """Serialize *data* as JSON and store it with the given TTL (seconds).

    No-op when *valkey* is ``None``.
    """
    if valkey is None:
        return
    try:
        await valkey.set(key, json.dumps(data), ex=ttl)
    except Exception:
        logger.warning("Valkey write failed for key %s", key, exc_info=True)


async def invalidate_pattern(valkey: Redis | None, pattern: str) -> int:
    """Delete all keys matching *pattern* (e.g. ``"crime:*"``).

    Uses ``SCAN`` to iterate without blocking.  Returns the number of keys
    deleted, or ``0`` when *valkey* is ``None``.
    """
    if valkey is None:
        return 0
    deleted = 0
    try:
        cursor: int | bytes = 0
        while True:
            cursor, keys = await valkey.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                deleted += await valkey.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning("Valkey invalidate failed for pattern %s", pattern, exc_info=True)
    return deleted
