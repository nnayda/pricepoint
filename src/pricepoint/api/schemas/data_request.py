"""Pydantic models for the data request endpoint."""

from datetime import datetime

from pydantic import BaseModel


class DataRequestCreate(BaseModel):
    """Request body for creating a data request."""

    address: str
    lat: float
    lon: float
    email: str | None = None


class DataRequestResponse(BaseModel):
    """Response body for a data request."""

    id: int
    address: str
    status: str
    created_at: datetime
