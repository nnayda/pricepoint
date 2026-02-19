"""Pydantic models for the greenspace endpoint."""

from pydantic import BaseModel


class GreenspaceFeature(BaseModel):
    """A single greenspace feature."""

    id: str
    name: str
    feature_type: str
    lat: float
    lon: float
    distance_miles: float
    acreage: float | None = None


class GreenspaceMetrics(BaseModel):
    """Aggregate greenspace metrics for the area."""

    parks_within_1mi: int
    nearest_park_miles: float
    nearest_greenway_miles: float = 0.0
    total_green_acres_1mi: float
    greenspace_z_score: float


class GreenspaceResponse(BaseModel):
    """Response body for greenspace data lookup."""

    features: list[GreenspaceFeature]
    metrics: GreenspaceMetrics
