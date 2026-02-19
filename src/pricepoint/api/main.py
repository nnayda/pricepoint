"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from pricepoint.api.routes import (
    auth,
    crime,
    forecast,
    geocode,
    greenspace,
    health,
    pois,
    property,
    saved,
    upload,
    utilities,
)
from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()

    # Startup: initialise Valkey/Redis connection pool
    if settings.valkey_url:
        pool = Redis.from_url(settings.valkey_url, decode_responses=True)
        app.state.valkey_pool = pool
        logger.info("Valkey connection pool initialised")
    else:
        app.state.valkey_pool = None
        logger.info("Valkey URL not configured; caching disabled")

    yield

    # Shutdown: close Valkey connection pool
    if app.state.valkey_pool is not None:
        await app.state.valkey_pool.aclose()
        logger.info("Valkey connection pool closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Home Value Forecast API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(forecast.router, prefix="/api")
    app.include_router(geocode.router, prefix="/api")
    app.include_router(property.router, prefix="/api")
    app.include_router(crime.router, prefix="/api")
    app.include_router(pois.router, prefix="/api")
    app.include_router(greenspace.router, prefix="/api")
    app.include_router(utilities.router, prefix="/api")
    app.include_router(saved.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")

    return app


app = create_app()
