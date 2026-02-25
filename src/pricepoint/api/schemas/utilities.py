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

    nearest_cell_tower_miles: float
    nearest_transmission_line_miles: float
    nearest_power_plant_miles: float
    nearest_pipeline_miles: float
    nuisance_score: float


class UtilitiesResponse(BaseModel):
    """Response body for utilities data lookup."""

    features: list[UtilityFeature]
    metrics: UtilitiesMetrics
