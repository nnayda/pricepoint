"""Pydantic models for the points of interest endpoint."""

from pydantic import BaseModel


class PointOfInterest(BaseModel):
    """A single point of interest."""

    id: str
    name: str
    category: str
    lat: float
    lon: float
    distance_miles: float
    drive_minutes: int


class PoisMetrics(BaseModel):
    """Aggregate metrics for POI results."""

    total_count: int
    categories_represented: int
    nearest_distance_miles: float | None


class PoisResponse(BaseModel):
    """Response body for points of interest lookup."""

    pois: list[PointOfInterest]
    metrics: PoisMetrics | None = None


class PoisSearchResponse(BaseModel):
    """Response body for POI search."""

    pois: list[PointOfInterest]
    total_count: int
    query: str
