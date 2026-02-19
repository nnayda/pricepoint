"""Saved-property endpoints — bookmark/unbookmark listings."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
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


@router.get("/saved", response_model=list[SavedPropertyResponse])
def list_saved(
    db: DbSession,
    user: AuthUser,
) -> list[SavedPropertyResponse]:
    """Return all saved properties for the authenticated user."""
    rows = db.execute(
        select(SavedProperty, RedfinListing.street_address)
        .outerjoin(RedfinListing, SavedProperty.listing_id == RedfinListing.id)
        .where(SavedProperty.user_id == user.id)
        .order_by(SavedProperty.created_at.desc())
    ).all()
    return [
        SavedPropertyResponse(
            id=sp.id,
            listing_id=sp.listing_id,
            notes=sp.notes,
            created_at=sp.created_at,
            listing_address=address,
        )
        for sp, address in rows
    ]


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

    return SavedPropertyResponse(
        id=saved.id,
        listing_id=saved.listing_id,
        notes=saved.notes,
        created_at=saved.created_at,
        listing_address=listing.street_address,
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

    listing = db.execute(
        select(RedfinListing).where(RedfinListing.id == saved.listing_id)
    ).scalar_one_or_none()

    return SavedPropertyResponse(
        id=saved.id,
        listing_id=saved.listing_id,
        notes=saved.notes,
        created_at=saved.created_at,
        listing_address=listing.street_address if listing else None,
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
