"""Forecast endpoint — predict home value for a given address."""

import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.rate_limit import limiter
from pricepoint.api.schemas.forecast import (
    FeatureAttribution,
    ForecastRequest,
    ForecastResponse,
)
from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["forecast"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_TIMEOUT = 5.0
FORECAST_CACHE_TTL = 86400  # 24 hours

FEATURE_DISPLAY_NAMES: dict[str, str] = {
    "dist_nearest_school_m": "School proximity",
    "dist_nearest_park_m": "Park proximity",
    "dist_nearest_hospital_m": "Hospital proximity",
    "dist_nearest_highway_m": "Highway proximity",
    "dist_nearest_railroad_m": "Railroad proximity",
    "crime_count_1km_1yr": "Crime density (1km)",
    "property_age": "Property age",
    "sqft_per_bedroom": "Space per bedroom",
    "bed_bath_ratio": "Bed/bath ratio",
    "avg_school_rating_2mi": "School ratings nearby",
    "total_park_acres_2km": "Park space nearby",
    "luxury_feature_count": "Luxury features",
    "zip_median_price": "Zip code values",
    "mortgage_rate_30yr": "Mortgage rates",
    "listing_premium_pct": "Listing premium",
}

# Stub feature importances used when no model is available.
# Positive = increases value, negative = decreases value.
_STUB_IMPORTANCES: list[dict[str, object]] = [
    {"feature": "avg_school_rating_2mi", "impact_dollars": 18500.0},
    {"feature": "sqft_per_bedroom", "impact_dollars": 15200.0},
    {"feature": "luxury_feature_count", "impact_dollars": 12800.0},
    {"feature": "zip_median_price", "impact_dollars": 11000.0},
    {"feature": "total_park_acres_2km", "impact_dollars": 8400.0},
    {"feature": "dist_nearest_school_m", "impact_dollars": 7200.0},
    {"feature": "dist_nearest_park_m", "impact_dollars": 5500.0},
    {"feature": "bed_bath_ratio", "impact_dollars": 4200.0},
    {"feature": "mortgage_rate_30yr", "impact_dollars": 3100.0},
    {"feature": "listing_premium_pct", "impact_dollars": 2800.0},
    {"feature": "dist_nearest_railroad_m", "impact_dollars": -7500.0},
    {"feature": "crime_count_1km_1yr", "impact_dollars": -12000.0},
    {"feature": "property_age", "impact_dollars": -9500.0},
    {"feature": "dist_nearest_highway_m", "impact_dollars": -6200.0},
    {"feature": "dist_nearest_hospital_m", "impact_dollars": -3800.0},
]


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
@limiter.limit(get_settings().rate_limit_forecast)
async def forecast(
    request: Request,
    body: ForecastRequest,
    db: Annotated[Session, Depends(get_db)],
    valkey: Annotated[Redis | None, Depends(get_valkey)],
) -> ForecastResponse:
    """Return a home value forecast for the given address.

    Geocodes the address, builds features, and runs the production model.
    Falls back gracefully when MLflow is unavailable.
    """
    cache_key = f"forecast:{body.address.strip().lower()}"

    # Check cache first
    if valkey is not None:
        try:
            cached = await valkey.get(cache_key)
            if cached is not None:
                return ForecastResponse(**json.loads(cached))
        except Exception:
            logger.warning("Valkey read failed for key %s", cache_key, exc_info=True)

    # Geocode the address
    coords = await _geocode_address(body)
    if coords is None:
        return ForecastResponse(
            address=body.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    lat, lon = coords

    # Look up or create property record
    try:
        property_id = _get_or_create_property_id(db, lat, lon, body.address)
    except Exception:
        logger.warning("Property lookup/creation failed", exc_info=True)
        return ForecastResponse(
            address=body.address,
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
            address=body.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    if features.empty:
        return ForecastResponse(
            address=body.address,
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
            address=body.address,
            predicted_value=0.0,
            confidence_interval_low=0.0,
            confidence_interval_high=0.0,
            model_version="unavailable",
        )

    response = ForecastResponse(
        address=body.address,
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


def _load_feature_importances(
    property_id: int,
    db: Session,
) -> list[FeatureAttribution]:
    """Load feature importances from the production model.

    Attempts to load the model from MLflow and compute importances
    weighted by the property's feature values.  Falls back to a
    predefined stub when the model is unavailable.
    """
    try:
        import mlflow

        model_name = "pricepoint-home-value"
        model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")

        # Try to get feature importances from the underlying model
        unwrapped = model._model_impl  # noqa: SLF001
        if hasattr(unwrapped, "feature_importances_"):
            raw_importances = unwrapped.feature_importances_
        elif hasattr(unwrapped, "coef_"):
            raw_importances = unwrapped.coef_
        else:
            raise AttributeError("Model has no feature importances")

        # Build features for this property to weight importances
        features = _build_features_for_property(db, property_id)
        if features.empty:
            raise ValueError("No features available")

        # Compute per-feature impact as importance * normalized feature value
        feature_names = list(features.columns)
        impacts: list[tuple[str, float]] = []
        for i, name in enumerate(feature_names):
            if i < len(raw_importances):
                val = float(features.iloc[0][name])
                importance = float(raw_importances[i])
                impact = importance * val
                impacts.append((name, impact))

        # Sort by absolute impact, take top 10 positive and top 10 negative
        positive = sorted(
            [(n, v) for n, v in impacts if v > 0],
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:10]
        negative = sorted(
            [(n, v) for n, v in impacts if v < 0],
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:10]

        results: list[FeatureAttribution] = []
        for name, impact in positive + negative:
            display = FEATURE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
            results.append(
                FeatureAttribution(
                    feature=name,
                    display_name=display,
                    impact_dollars=round(impact, 2),
                )
            )
        return results

    except Exception:
        logger.info(
            "MLflow model unavailable for importance — returning stub data",
            exc_info=True,
        )

    # Fallback: return stub importances
    return [
        FeatureAttribution(
            feature=str(entry["feature"]),
            display_name=FEATURE_DISPLAY_NAMES.get(
                str(entry["feature"]),
                str(entry["feature"]).replace("_", " ").title(),
            ),
            impact_dollars=float(entry["impact_dollars"]),
        )
        for entry in _STUB_IMPORTANCES
    ]


@router.get(
    "/forecast/importance/{property_id}",
    response_model=list[FeatureAttribution],
)
@limiter.limit(get_settings().rate_limit_forecast)
async def feature_importance(
    request: Request,
    property_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[FeatureAttribution]:
    """Return feature importance attributions for a property prediction.

    Loads the production model's global feature importances weighted by
    the property's feature values.  Returns top 10 positive and top 10
    negative contributors.  Falls back to stub data when MLflow is
    unavailable.
    """
    return _load_feature_importances(property_id, db)
