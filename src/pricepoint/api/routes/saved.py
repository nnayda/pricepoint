"""Saved-property endpoints — bookmark/unbookmark listings."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.api.auth import get_current_user
from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.saved import (
    SavedPropertyCreate,
    SavedPropertyResponse,
    SavedPropertyUpdate,
)
from pricepoint.db.models import RedfinListing, SavedProperty, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["saved"])

DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[User, Depends(get_current_user)]


def _first_photo_url(photos: list[str] | None) -> str | None:
    """Build /api/photos/ URL from the first element of property_photos JSON."""
    if photos and len(photos) > 0:
        return f"/api/photos/{photos[0]}"
    return None


def _build_response(sp: SavedProperty, row: object) -> SavedPropertyResponse:
    """Build an enriched SavedPropertyResponse from a query row."""
    return SavedPropertyResponse(
        id=sp.id,
        listing_id=sp.listing_id,
        notes=sp.notes,
        created_at=sp.created_at,
        listing_address=getattr(row, "street_address", None),
        city=getattr(row, "city", None),
        state=getattr(row, "state", None),
        zip_code=getattr(row, "zip_code", None),
        listing_status=getattr(row, "listing_status", None),
        listing_price=getattr(row, "listing_price", None),
        sold_price=getattr(row, "sold_price", None),
        num_beds=getattr(row, "num_beds", None),
        num_baths=getattr(row, "num_baths", None),
        sqft=getattr(row, "sqft", None),
        year_built=getattr(row, "year_built", None),
        photo_url=_first_photo_url(getattr(row, "property_photos", None)),
        lat=getattr(row, "lat", None),
        lon=getattr(row, "lon", None),
    )


@router.get("/saved", response_model=list[SavedPropertyResponse])
def list_saved(
    db: DbSession,
    user: AuthUser,
) -> list[SavedPropertyResponse]:
    """Return all saved properties for the authenticated user."""
    rows = db.execute(
        select(
            SavedProperty,
            RedfinListing.street_address,
            RedfinListing.city,
            RedfinListing.state,
            RedfinListing.zip_code,
            RedfinListing.listing_status,
            RedfinListing.listing_price,
            RedfinListing.sold_price,
            RedfinListing.num_beds,
            RedfinListing.num_baths,
            RedfinListing.sqft,
            RedfinListing.year_built,
            RedfinListing.property_photos,
            ST_Y(RedfinListing.location).label("lat"),
            ST_X(RedfinListing.location).label("lon"),
        )
        .outerjoin(RedfinListing, SavedProperty.listing_id == RedfinListing.id)
        .where(SavedProperty.user_id == user.id)
        .order_by(SavedProperty.created_at.desc())
    ).all()
    return [_build_response(row[0], row) for row in rows]


@router.post("/saved", response_model=SavedPropertyResponse, status_code=status.HTTP_201_CREATED)
def save_property(
    body: SavedPropertyCreate,
    db: DbSession,
    user: AuthUser,
) -> SavedPropertyResponse:
    """Bookmark a property listing for the authenticated user."""
    # Check listing exists
    listing = db.execute(
        select(RedfinListing).where(RedfinListing.id == body.listing_id)
    ).scalar_one_or_none()
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    # Check for duplicate
    existing = db.execute(
        select(SavedProperty).where(
            SavedProperty.user_id == user.id,
            SavedProperty.listing_id == body.listing_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property already saved",
        )

    saved = SavedProperty(
        user_id=user.id,
        listing_id=body.listing_id,
        notes=body.notes,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    photos = listing.property_photos if listing.property_photos else None
    lat_val = None
    lon_val = None
    if listing.location is not None:
        coords = db.execute(
            select(
                ST_Y(RedfinListing.location).label("lat"),
                ST_X(RedfinListing.location).label("lon"),
            ).where(RedfinListing.id == listing.id)
        ).one()
        lat_val = coords.lat
        lon_val = coords.lon

    return SavedPropertyResponse(
        id=saved.id,
        listing_id=saved.listing_id,
        notes=saved.notes,
        created_at=saved.created_at,
        listing_address=listing.street_address,
        city=listing.city,
        state=listing.state,
        zip_code=listing.zip_code,
        listing_status=listing.listing_status,
        listing_price=listing.listing_price,
        sold_price=listing.sold_price,
        num_beds=listing.num_beds,
        num_baths=listing.num_baths,
        sqft=listing.sqft,
        year_built=listing.year_built,
        photo_url=_first_photo_url(photos),
        lat=lat_val,
        lon=lon_val,
    )


@router.put("/saved/{saved_id}", response_model=SavedPropertyResponse)
def update_saved(
    saved_id: int,
    body: SavedPropertyUpdate,
    db: DbSession,
    user: AuthUser,
) -> SavedPropertyResponse:
    """Update notes on a saved property. Must be the owner."""
    saved = db.execute(
        select(SavedProperty).where(SavedProperty.id == saved_id)
    ).scalar_one_or_none()

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved property not found",
        )
    if saved.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to modify this saved property",
        )

    saved.notes = body.notes
    db.commit()
    db.refresh(saved)

    row = db.execute(
        select(
            RedfinListing.street_address,
            RedfinListing.city,
            RedfinListing.state,
            RedfinListing.zip_code,
            RedfinListing.listing_status,
            RedfinListing.listing_price,
            RedfinListing.sold_price,
            RedfinListing.num_beds,
            RedfinListing.num_baths,
            RedfinListing.sqft,
            RedfinListing.year_built,
            RedfinListing.property_photos,
            ST_Y(RedfinListing.location).label("lat"),
            ST_X(RedfinListing.location).label("lon"),
        ).where(RedfinListing.id == saved.listing_id)
    ).one_or_none()

    return SavedPropertyResponse(
        id=saved.id,
        listing_id=saved.listing_id,
        notes=saved.notes,
        created_at=saved.created_at,
        listing_address=getattr(row, "street_address", None) if row else None,
        city=getattr(row, "city", None) if row else None,
        state=getattr(row, "state", None) if row else None,
        zip_code=getattr(row, "zip_code", None) if row else None,
        listing_status=getattr(row, "listing_status", None) if row else None,
        listing_price=getattr(row, "listing_price", None) if row else None,
        sold_price=getattr(row, "sold_price", None) if row else None,
        num_beds=getattr(row, "num_beds", None) if row else None,
        num_baths=getattr(row, "num_baths", None) if row else None,
        sqft=getattr(row, "sqft", None) if row else None,
        year_built=getattr(row, "year_built", None) if row else None,
        photo_url=_first_photo_url(getattr(row, "property_photos", None)) if row else None,
        lat=getattr(row, "lat", None) if row else None,
        lon=getattr(row, "lon", None) if row else None,
    )


@router.delete("/saved/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved(
    saved_id: int,
    db: DbSession,
    user: AuthUser,
) -> None:
    """Remove a saved property. Must be the owner."""
    saved = db.execute(
        select(SavedProperty).where(SavedProperty.id == saved_id)
    ).scalar_one_or_none()

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved property not found",
        )
    if saved.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this saved property",
        )

    db.delete(saved)
    db.commit()
