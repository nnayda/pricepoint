"""Forecast endpoint — predict home value for a given address."""

import json
import logging
from typing import Annotated

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
from pricepoint.api.services.geocoding import geocode_async
from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["forecast"])

FORECAST_CACHE_TTL = 86400  # 24 hours

FEATURE_GROUPS: dict[str, str] = {
    "sqft": "Property",
    "num_beds": "Property",
    "num_baths": "Property",
    "lot_size": "Property",
    "year_built": "Property",
    "num_stories": "Property",
    "num_garage_spaces": "Property",
    "has_fireplace": "Property",
    "has_private_pool": "Property",
    "has_community_pool": "Property",
    "property_age": "Property",
    "sqft_per_bedroom": "Property",
    "bed_bath_ratio": "Property",
    "luxury_feature_count": "Property",
    "dist_nearest_school_m": "Location",
    "dist_nearest_park_m": "Location",
    "dist_nearest_hospital_m": "Location",
    "crime_count_1km_1yr": "Location",
    "avg_school_rating_2mi": "Location",
    "total_park_acres_2km": "Location",
    "zip_median_price": "Location",
    "listing_premium_pct": "Location",
    "mortgage_rate_30yr": "Economic",
    "unemployment_rate": "Economic",
    "cpi_yoy": "Economic",
    "median_household_income": "Economic",
}

FEATURE_DISPLAY_NAMES: dict[str, str] = {
    "dist_nearest_school_m": "School proximity",
    "dist_nearest_park_m": "Park proximity",
    "dist_nearest_hospital_m": "Hospital proximity",
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
    {"feature": "crime_count_1km_1yr", "impact_dollars": -12000.0},
    {"feature": "property_age", "impact_dollars": -9500.0},
    {"feature": "dist_nearest_hospital_m", "impact_dollars": -3800.0},
]


async def _geocode_address(request: ForecastRequest) -> tuple[float, float] | None:
    """Geocode the address via configured provider, returning (lat, lon) or None."""
    parts = [request.address]
    if request.city:
        parts.append(request.city)
    if request.state:
        parts.append(request.state)
    if request.zip_code:
        parts.append(request.zip_code)
    query = ", ".join(parts)

    results = await geocode_async(query, limit=1)
    if not results:
        return None

    return results[0]["lat"], results[0]["lon"]


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
    """Compute per-instance SHAP values for a property prediction.

    Attempts to load the production model from MLflow and compute
    true Shapley values using ``shap.TreeExplainer``.  Each value
    represents the feature's dollar contribution to the prediction.
    Falls back to a predefined stub when the model is unavailable.
    """
    try:
        from pricepoint.models.inference import compute_shap_values, load_production_model

        info = load_production_model()
        if info is None:
            raise RuntimeError("No production model available")

        model = info.model

        # Build features for this property
        features = _build_features_for_property(db, property_id)
        if features.empty:
            raise ValueError("No features available")

        # Drop target column if present
        if "sold_price" in features.columns:
            features = features.drop(columns=["sold_price"])

        shap_results = compute_shap_values(model, features)

        # Take top 10 positive and top 10 negative
        positive = [r for r in shap_results if float(r["shap_value"]) > 0][:10]
        negative = [r for r in shap_results if float(r["shap_value"]) < 0][:10]

        results: list[FeatureAttribution] = []
        for entry in positive + negative:
            name = str(entry["feature"])
            display = FEATURE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
            group = FEATURE_GROUPS.get(name, "Other")
            results.append(
                FeatureAttribution(
                    feature=name,
                    display_name=display,
                    impact_dollars=round(float(entry["shap_value"]), 2),
                    group=group,
                )
            )
        return results

    except Exception:
        logger.info(
            "SHAP computation unavailable — returning stub data",
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
            group=FEATURE_GROUPS.get(str(entry["feature"]), "Other"),
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
