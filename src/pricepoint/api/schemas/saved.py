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

    # Enriched fields from RedfinListing
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    listing_status: str | None = None
    listing_price: float | None = None
    sold_price: float | None = None
    num_beds: int | None = None
    num_baths: float | None = None
    sqft: int | None = None
    year_built: int | None = None
    photo_url: str | None = None
    lat: float | None = None
    lon: float | None = None

    model_config = {"from_attributes": True}
