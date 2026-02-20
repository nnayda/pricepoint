"""API rate limiting using slowapi with Valkey/Redis backend (in-memory fallback)."""

import logging

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)


def _build_storage_uri() -> str:
    """Return the storage URI for the rate limiter.

    Uses Valkey/Redis when configured, otherwise falls back to in-memory.
    """
    settings = get_settings()
    if settings.valkey_url:
        logger.info("Rate limiter using Valkey backend: %s", settings.valkey_url)
        return settings.valkey_url
    logger.info("Rate limiter using in-memory backend")
    return "memory://"


def create_limiter(*, storage_uri: str | None = None) -> Limiter:
    """Create a Limiter instance.

    Parameters
    ----------
    storage_uri:
        Explicit storage URI.  When *None* the URI is derived from
        application settings (Valkey URL or ``memory://``).
    """
    settings = get_settings()
    uri = storage_uri if storage_uri is not None else _build_storage_uri()

    return Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_default],
        storage_uri=uri,
    )


# Module-level limiter used by route decorators.
# Uses in-memory storage so that importing this module never requires a
# running Valkey/Redis instance.  The ``setup_rate_limiting`` function
# wires it into the FastAPI app at startup.
limiter = create_limiter(storage_uri="memory://")


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """Inject X-RateLimit-* headers after the SlowAPI decorator has run.

    SlowAPI's built-in ``SlowAPIMiddleware`` only injects headers when it
    can resolve the route handler from top-level routes.  With FastAPI's
    nested ``APIRouter(prefix=...)`` pattern the handler lookup fails, so
    headers are never added.  This middleware runs *after* the SlowAPI
    middleware and reads the ``view_rate_limit`` state set by the
    ``@limiter.limit()`` decorator to inject the headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        view_rate_limit = getattr(request.state, "view_rate_limit", None)
        if view_rate_limit is not None:
            rate_limit_item, identifiers = view_rate_limit
            try:
                window_stats = limiter.limiter.get_window_stats(rate_limit_item, *identifiers)
                response.headers["X-RateLimit-Limit"] = str(rate_limit_item.amount)
                response.headers["X-RateLimit-Remaining"] = str(window_stats[1])
                response.headers["X-RateLimit-Reset"] = str(1 + window_stats[0])
            except Exception:
                logger.debug("Failed to inject rate limit headers", exc_info=True)

        return response


def setup_rate_limiting(app: FastAPI) -> None:
    """Wire rate limiting into a FastAPI application.

    Adds the limiter to app state, registers the SlowAPI middleware, and
    installs the exception handler for 429 responses.
    """
    app.state.limiter = limiter
    app.add_middleware(RateLimitHeaderMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
