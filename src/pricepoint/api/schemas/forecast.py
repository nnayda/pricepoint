"""Pydantic models for the forecast endpoint."""

from pydantic import BaseModel


class ForecastRequest(BaseModel):
    """Request body for a home value forecast."""

    address: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None


class ForecastResponse(BaseModel):
    """Response body with predicted home value and confidence interval."""

    address: str
    predicted_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    model_version: str


class FeatureAttribution(BaseModel):
    """A single feature's contribution to the predicted value."""

    feature: str
    display_name: str
    impact_dollars: float
