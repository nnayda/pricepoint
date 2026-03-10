"""Saved POI CRUD endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.api.auth import get_current_user
from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.pois import (
    SavedPoiCreate,
    SavedPoiResponse,
    SavedPoiUpdate,
)
from pricepoint.db.models import Place, SavedPoi, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["saved-pois"])

DbSession = Annotated[Session, Depends(get_db)]
AuthUser = Annotated[User, Depends(get_current_user)]


def _to_response(r: SavedPoi) -> SavedPoiResponse:
    return SavedPoiResponse(
        id=r.id,
        match_type=r.match_type,
        match_value=r.match_value,
        display_name=r.display_name,
        category=r.category,
        user_category=r.user_category,
        marker_color=r.marker_color,
        marker_image_url=r.marker_image_url,
        created_at=r.created_at,
    )


@router.get("/saved-pois", response_model=list[SavedPoiResponse])
def list_saved_pois(
    db: DbSession,
    user: AuthUser,
) -> list[SavedPoiResponse]:
    """Return all saved POIs for the authenticated user."""
    rows = (
        db.execute(
            select(SavedPoi).where(SavedPoi.user_id == user.id).order_by(SavedPoi.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [_to_response(r) for r in rows]


@router.post(
    "/saved-pois",
    response_model=SavedPoiResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_poi(
    body: SavedPoiCreate,
    db: DbSession,
    user: AuthUser,
) -> SavedPoiResponse:
    """Save a POI for proximity tracking. Validates the match exists in places."""
    # Validate existence in places table
    if body.match_type == "brand":
        exists = db.execute(
            select(Place.id).where(Place.brand_name == body.match_value).limit(1)
        ).scalar_one_or_none()
    else:
        exists = db.execute(
            select(Place.id).where(Place.name == body.match_value).limit(1)
        ).scalar_one_or_none()

    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No places found matching {body.match_type}={body.match_value!r}",
        )

    # Check duplicate
    existing = db.execute(
        select(SavedPoi).where(
            SavedPoi.user_id == user.id,
            SavedPoi.match_type == body.match_type,
            SavedPoi.match_value == body.match_value,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="POI already saved",
        )

    saved = SavedPoi(
        user_id=user.id,
        match_type=body.match_type,
        match_value=body.match_value,
        display_name=body.display_name,
        category=body.category,
        user_category=body.user_category,
        marker_color=body.marker_color,
        marker_image_url=body.marker_image_url,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return _to_response(saved)


@router.patch(
    "/saved-pois/{saved_poi_id}",
    response_model=SavedPoiResponse,
)
def update_saved_poi(
    saved_poi_id: int,
    body: SavedPoiUpdate,
    db: DbSession,
    user: AuthUser,
) -> SavedPoiResponse:
    """Partially update a saved POI. Must be the owner."""
    saved = db.execute(select(SavedPoi).where(SavedPoi.id == saved_poi_id)).scalar_one_or_none()

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved POI not found",
        )
    if saved.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to update this saved POI",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(saved, field, value)

    db.commit()
    db.refresh(saved)
    return _to_response(saved)


@router.delete("/saved-pois/{saved_poi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_poi(
    saved_poi_id: int,
    db: DbSession,
    user: AuthUser,
) -> None:
    """Remove a saved POI. Must be the owner."""
    saved = db.execute(select(SavedPoi).where(SavedPoi.id == saved_poi_id)).scalar_one_or_none()

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved POI not found",
        )
    if saved.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this saved POI",
        )

    db.delete(saved)
    db.commit()
