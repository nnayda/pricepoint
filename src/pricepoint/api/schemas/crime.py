"""Pydantic models for the crime endpoint."""

from pydantic import BaseModel


class CrimeHeatmapPoint(BaseModel):
    """A single heatmap data point."""

    lat: float
    lon: float
    intensity: float


class CrimeIncident(BaseModel):
    """A single crime incident record."""

    id: str
    incident_type: str
    category: str
    date: str
    lat: float
    lon: float
    description: str | None = None


class CrimeMetrics(BaseModel):
    """Aggregate crime metrics for the area."""

    total_incidents_1mi: int
    incidents_per_1000_people: float
    crime_z_score: float
    trend: str


class CrimeResponse(BaseModel):
    """Response body for crime data lookup."""

    heatmap: list[CrimeHeatmapPoint]
    incidents: list[CrimeIncident]
    metrics: CrimeMetrics
