"""Pydantic models for saved-property endpoints."""

from datetime import datetime

from pydantic import BaseModel


class SavedPropertyCreate(BaseModel):
    """Request body to save/bookmark a property."""

    listing_id: int
    notes: str | None = None


class SavedPropertyUpdate(BaseModel):
    """Request body to update notes on a saved property."""

    notes: str | None = None


class SavedPropertyResponse(BaseModel):
    """Single saved-property record returned to the client."""

    id: int
    listing_id: int
    notes: str | None = None
    created_at: datetime
    listing_address: str | None = None

    model_config = {"from_attributes": True}
