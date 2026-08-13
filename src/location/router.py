from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, require_staff_user
from src.db.connection import get_db
from src.location import service
from src.location.schemas import LocationCreate, LocationRead, LocationUpdate
from src.user.schemas import UserRead

router = APIRouter()


@router.get("", response_model=list[LocationRead])
def list_locations(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LocationRead]:
    return service.list_locations(db)


@router.get("/{location_id}", response_model=LocationRead)
def get_location(
    location_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationRead:
    location = service.get_location(db, location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    return location


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> LocationRead:
    location = service.create_location(db, payload)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parent location",
        )
    return location


@router.patch("/{location_id}", response_model=LocationRead)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> LocationRead:
    location = service.update_location(db, location_id, payload)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found or invalid parent location",
        )
    return location
