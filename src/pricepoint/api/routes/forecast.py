"""Forecast endpoint — predict home value for a given address."""

from fastapi import APIRouter

from pricepoint.api.schemas.forecast import ForecastRequest, ForecastResponse

router = APIRouter(tags=["forecast"])


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(request: ForecastRequest) -> ForecastResponse:
    """Return a home value forecast for the given address.

    This is a stub — real implementation will geocode the address,
    build features, and run the production model.
    """
    return ForecastResponse(
        address=request.address,
        predicted_value=0.0,
        confidence_interval_low=0.0,
        confidence_interval_high=0.0,
        model_version="stub",
    )
