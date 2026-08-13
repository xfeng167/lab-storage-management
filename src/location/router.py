from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.auth.dependencies import require_catalog_manager, require_location_reader
from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from src.core.errors import business_error, conflict, not_found
from src.db.connection import get_db
from src.location import service
from src.location.schemas import LocationCreate, LocationRead, LocationUpdate
from src.user.schemas import UserRead

router = APIRouter()


@router.get("", response_model=Page[LocationRead])
def list_locations(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_location_reader),
    db: Session = Depends(get_db),
) -> Page[LocationRead]:
    return service.list_locations(db, page=page, size=size)


@router.get("/{location_id}", response_model=LocationRead)
def get_location(
    location_id: int,
    current_user: UserRead = Depends(require_location_reader),
    db: Session = Depends(get_db),
) -> LocationRead:
    location = service.get_location(db, location_id)
    if location is None:
        raise not_found("LOCATION_NOT_FOUND", "Location not found")
    return location


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    current_user: UserRead = Depends(require_catalog_manager),
    db: Session = Depends(get_db),
) -> LocationRead:
    location, error = service.create_location(db, payload)
    if location is None:
        if error == "hierarchy_busy":
            raise business_error(
                "LOCATION_HIERARCHY_BUSY",
                "Location hierarchy is being updated; retry the request",
                status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "1"},
            )
        if error == "parent_not_found":
            raise not_found("PARENT_LOCATION_NOT_FOUND", "Parent location not found")
        raise conflict("LOCATION_HIERARCHY_CYCLE", "Location hierarchy cannot contain a cycle")
    return location


@router.patch("/{location_id}", response_model=LocationRead)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    current_user: UserRead = Depends(require_catalog_manager),
    db: Session = Depends(get_db),
) -> LocationRead:
    location, error = service.update_location(db, location_id, payload)
    if location is None:
        if error == "hierarchy_busy":
            raise business_error(
                "LOCATION_HIERARCHY_BUSY",
                "Location hierarchy is being updated; retry the request",
                status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "1"},
            )
        if error == "cycle":
            raise conflict(
                "LOCATION_HIERARCHY_CYCLE",
                "Location hierarchy cannot contain a cycle",
            )
        if error == "parent_not_found":
            raise not_found("PARENT_LOCATION_NOT_FOUND", "Parent location not found")
        raise not_found("LOCATION_NOT_FOUND", "Location not found")
    return location
