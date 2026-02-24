"""Pydantic models for the geocode endpoint."""

from pydantic import BaseModel


class GeocodeResult(BaseModel):
    """A single geocoding result."""

    display_name: str
    lat: float
    lon: float
    place_id: int | None = None
    osm_type: str
    osm_id: int
    boundingbox: list[float] = []


class GeocodeResponse(BaseModel):
    """Response body for geocode lookups."""

    results: list[GeocodeResult]
    cached: bool
