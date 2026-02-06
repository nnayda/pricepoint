"""Pydantic models for the utilities endpoint."""

from pydantic import BaseModel


class UtilityFeature(BaseModel):
    """A single utility infrastructure feature."""

    id: str
    name: str
    feature_type: str
    lat: float
    lon: float
    distance_miles: float


class UtilitiesMetrics(BaseModel):
    """Aggregate utilities metrics for the area."""

    nearest_highway_miles: float
    nearest_railroad_miles: float
    nearest_powerline_miles: float
    nuisance_score: float


class UtilitiesResponse(BaseModel):
    """Response body for utilities data lookup."""

    features: list[UtilityFeature]
    metrics: UtilitiesMetrics
