"""Data request endpoints — allow users to request data for unlisted properties."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from pricepoint.api.dependencies import get_db
from pricepoint.api.schemas.data_request import DataRequestCreate, DataRequestResponse
from pricepoint.db.models import DataRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-requests"])


@router.post("/data-requests", response_model=DataRequestResponse, status_code=201)
async def create_data_request(
    body: DataRequestCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DataRequestResponse:
    """Create a data request for a property not yet in the database.

    Deduplicates: if a pending or processing request already exists for the
    same address, the existing request is returned instead of creating a new one.
    """
    existing = db.execute(
        select(DataRequest).where(
            DataRequest.address == body.address,
            DataRequest.status.in_(["pending", "processing"]),
        )
    ).scalar_one_or_none()

    if existing:
        return DataRequestResponse(
            id=existing.id,
            address=existing.address,
            status=existing.status,
            created_at=existing.created_at,
        )

    data_request = DataRequest(
        address=body.address,
        lat=body.lat,
        lon=body.lon,
        status="pending",
        requested_by_email=body.email,
    )
    db.add(data_request)
    db.commit()
    db.refresh(data_request)

    return DataRequestResponse(
        id=data_request.id,
        address=data_request.address,
        status=data_request.status,
        created_at=data_request.created_at,
    )


@router.get("/data-requests/{request_id}", response_model=DataRequestResponse)
async def get_data_request(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> DataRequestResponse:
    """Check the status of a data request."""
    data_request = db.execute(
        select(DataRequest).where(DataRequest.id == request_id)
    ).scalar_one_or_none()

    if not data_request:
        raise HTTPException(status_code=404, detail="Data request not found")

    return DataRequestResponse(
        id=data_request.id,
        address=data_request.address,
        status=data_request.status,
        created_at=data_request.created_at,
    )
