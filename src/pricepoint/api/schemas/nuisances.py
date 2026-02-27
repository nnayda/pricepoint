"""Pydantic models for the nuisances endpoint."""

from pydantic import BaseModel


class NuisanceSource(BaseModel):
    """A single nuisance source near the property."""

    id: str
    name: str
    source_type: str  # "aviation" | "road" | "rail"
    severity: str  # "Caution" | "Concern"
    distance_miles: float
    lat: float | None = None
    lon: float | None = None
    detail: str
    noise_min_db: int | None = None
    noise_band: str | None = None


class NuisanceSourcesResponse(BaseModel):
    """List of nuisance sources near a property."""

    sources: list[NuisanceSource]
