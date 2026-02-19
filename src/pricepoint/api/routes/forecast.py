"""Forecast endpoint — predict home value for a given address."""

import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.schemas.forecast import ForecastRequest, ForecastResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["forecast"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_TIMEOUT = 5.0
FORECAST_CACHE_TTL = 86400  # 24 hours


async def _geocode_address(request: ForecastRequest) -> tuple[float, float] | None:
    """Geocode the address via Nominatim, returning (lat, lon) or None."""
    parts = [request.address]
    if request.city:
        parts.append(request.city)
    if request.state:
        parts.append(request.state)
    if request.zip_code:
        parts.append(request.zip_code)
    query = ", ".join(parts)

    try:
        async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
                headers={"User-Agent": "PricePoint/0.1.0"},
            )
            resp.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Geocoding failed for %r", query, exc_info=True)
        return None

    results = resp.json()
    if not results:
        return None

    return float(results[0]["lat"]), float(results[0]["lon"])


def _build_features_for_property(
    db: Session,
    property_id: int,
) -> "pd.DataFrame":  # noqa: F821
    """Assemble features for a single property."""
    import pandas as pd

    from pricepoint.features.assembly import assemble_features

    features = assemble_features(db, property_ids=[property_id])
    if features.empty:
        return pd.DataFrame()
    return features


def _load_model_and_predict(
    features: "pd.DataFrame",  # noqa: F821
) -> tuple[float, float, float, str]:
    """Load the production model from MLflow and generate a prediction.

    Returns (predicted_value, ci_low, ci_high, model_version).
    """
    import mlflow
    import numpy as np

    model_name = "pricepoint-home-value"
    model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
    model_version = model.metadata.run_id

    prediction = model.predict(features)
    predicted_value = float(np.mean(prediction))

    # Approximate 90% confidence interval using +/- 10% of predicted value
    margin = predicted_value * 0.10
    ci_low = predicted_value - margin
    ci_high = predicted_value + margin

    return predicted_value, ci_low, ci_high, model_version


def _get_or_create_property_id(
    db: Session,
    lat: float,
    lon: float,
    address: str,
) -> int:
    """Look up an existing property by coordinates or create a temporary record.

    Returns the property_id.
    """
    from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID

    from pricepoint.db.models import PropertyDetail

    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    existing = (
        db.query(PropertyDetail.id)
        .filter(ST_DWithin(PropertyDetail.location, point, 0.0005))
        .first()
    )
    if existing:
        return existing[0]

    # Create a temporary property record for feature engineering
    prop = PropertyDetail(
        address=address,
        location=f"SRID=4326;POINT({lon} {lat})",
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop.id


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(
    request: ForecastRequest,
    db: Annotated[Session, Depends(get_db)],
    valkey: Annotated[Redis | None, Depends(get_valkey)],
) -> ForecastResponse:
    """Return a home value forecast for the given address.

    Geocodes the address, builds features, and runs the production model.
    Falls back gracefully when MLflow is unavailable.
    """
    cache_key = f"forecast:{request.address.strip().lower()}"

    # Check cache first
    if valkey is not None:
        try:
            cached = await valkey.get(cache_key)
            if cached is not None:
                return ForecastResponse(**json.loads(cached))
        except Exception:
            logger.warning("Valkey read failed for key %s", cache_key, exc_info=True)

    # Geocode the address
    coords = await _geocode_address(request)
    if coords is None:
        return ForecastResponse(
            address=request.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    lat, lon = coords

    # Look up or create property record
    try:
        property_id = _get_or_create_property_id(db, lat, lon, request.address)
    except Exception:
        logger.warning("Property lookup/creation failed", exc_info=True)
        return ForecastResponse(
            address=request.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    # Build features for this property
    try:
        features = _build_features_for_property(db, property_id)
    except Exception:
        logger.warning("Feature engineering failed for property %d", property_id, exc_info=True)
        return ForecastResponse(
            address=request.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    if features.empty:
        return ForecastResponse(
            address=request.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    # Load model and predict
    try:
        predicted_value, ci_low, ci_high, model_version = _load_model_and_predict(features)
    except Exception:
        logger.warning("Model prediction failed", exc_info=True)
        return ForecastResponse(
            address=request.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    response = ForecastResponse(
        address=request.address,
        predicted_value=predicted_value,
        confidence_interval_low=ci_low,
        confidence_interval_high=ci_high,
        model_version=model_version,
    )

    # Cache the result
    if valkey is not None:
        try:
            await valkey.set(
                cache_key,
                json.dumps(response.model_dump()),
                ex=FORECAST_CACHE_TTL,
            )
        except Exception:
            logger.warning("Valkey write failed for key %s", cache_key, exc_info=True)

    return response
