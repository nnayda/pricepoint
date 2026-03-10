"""Pydantic models for the points of interest endpoint."""

from datetime import datetime

from pydantic import BaseModel, Field


class PointOfInterest(BaseModel):
    """A single point of interest."""

    id: str
    name: str
    category: str
    lat: float
    lon: float
    distance_miles: float
    drive_minutes: int
    subcategory: str | None = None
    address: str | None = None


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


# --- Saved POIs schemas ---


class PoiAutocompleteItem(BaseModel):
    """A single autocomplete suggestion."""

    match_type: str  # "brand" or "name"
    match_value: str
    display_name: str
    category: str | None = None
    count: int


class PoiAutocompleteResponse(BaseModel):
    """Autocomplete results for POI search."""

    results: list[PoiAutocompleteItem]
    query: str


class SavedPoiCreate(BaseModel):
    """Request body to save a POI."""

    match_type: str = Field(pattern=r"^(brand|name)$")
    match_value: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    category: str | None = None
    user_category: str | None = None
    marker_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    marker_image_url: str | None = None
    alternate_names: list[str] | None = None


class SavedPoiUpdate(BaseModel):
    """Request body to partially update a saved POI."""

    user_category: str | None = None
    marker_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    marker_image_url: str | None = None
    alternate_names: list[str] | None = None


class SavedPoiResponse(BaseModel):
    """A single saved POI."""

    id: int
    match_type: str
    match_value: str
    display_name: str
    category: str | None = None
    user_category: str | None = None
    marker_color: str | None = None
    marker_image_url: str | None = None
    alternate_names: list[str] | None = None
    created_at: datetime


class SavedPoiMatch(BaseModel):
    """A nearby location matching a saved POI."""

    id: str
    name: str
    address: str | None = None
    lat: float
    lon: float
    distance_miles: float
    drive_minutes: int


class SavedPoiNearbyGroup(BaseModel):
    """A saved POI with its nearby matching locations."""

    saved_poi_id: int
    display_name: str
    category: str | None = None
    match_type: str
    matches: list[SavedPoiMatch]
    user_category: str | None = None
    marker_color: str | None = None
    marker_image_url: str | None = None


class SavedPoiNearbyResponse(BaseModel):
    """Grouped nearby results for all saved POIs."""

    groups: list[SavedPoiNearbyGroup]
