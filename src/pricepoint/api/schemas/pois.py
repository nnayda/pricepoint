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


class PoisResponse(BaseModel):
    """Response body for points of interest lookup."""

    pois: list[PointOfInterest]
