from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.auth.dependencies import (
    require_catalog_manager,
    require_inventory_manager,
    require_material_reader,
)
from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from src.core.errors import bad_request, conflict, not_found
from src.db.connection import get_db
from src.material import service
from src.material.schemas import (
    MaterialCreate,
    MaterialMove,
    MaterialRead,
    MaterialUpdate,
    QuantityAdjustment,
    QuantityChange,
)
from src.user.schemas import UserRead

router = APIRouter()


def _raise_inventory_error(error: str | None) -> None:
    if error == "not_found":
        raise not_found("MATERIAL_NOT_FOUND", "Material not found")
    if error == "archived":
        raise conflict("MATERIAL_ARCHIVED", "Archived material cannot be changed")
    if error == "insufficient_quantity":
        raise conflict("INVENTORY_INSUFFICIENT", "Insufficient quantity available")
    if error == "invalid_location":
        raise not_found("LOCATION_NOT_FOUND", "Location not found")
    raise bad_request("INVENTORY_OPERATION_FAILED", "Inventory operation failed")

@router.get("", response_model=Page[MaterialRead])
def list_materials(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_material_reader),
    db: Session = Depends(get_db),
) -> Page[MaterialRead]:
    return service.list_materials(db, page=page, size=size)

@router.get("/search", response_model=Page[MaterialRead])
def search_materials(
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    material_type: str | None = None,
    source: str | None = None,
    qc_status: Literal["pending", "passed", "failed"] | None = None,
    availability_status: Literal["available", "low_stock", "unavailable"] | None = None,
    location_id: int | None = None,
    low_stock: bool = False,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_material_reader),
    db: Session = Depends(get_db),
) -> Page[MaterialRead]:
    return service.search_materials(
        db,
        keyword=keyword,
        material_type=material_type,
        source=source,
        qc_status=qc_status,
        availability_status=availability_status,
        location_id=location_id,
        low_stock=low_stock,
        include_archived=include_archived,
        page=page,
        size=size,
    )

@router.get("/{material_id}", response_model=MaterialRead)
def get_material(
    material_id: int,
    current_user: UserRead = Depends(require_material_reader),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = service.get_material(db, material_id)
    if material is None:
        raise not_found("MATERIAL_NOT_FOUND", "Material not found")
    return material

@router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    current_user: UserRead = Depends(require_catalog_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.create_material(db, payload)
    if material is None:
        if error == "duplicate_code":
            raise conflict("MATERIAL_CODE_CONFLICT", "Material code already exists")
        if error == "invalid_location":
            raise not_found("LOCATION_NOT_FOUND", "Location not found")
        raise bad_request("MATERIAL_CREATE_FAILED", "Material creation failed")
    return material

@router.patch("/{material_id}", status_code=status.HTTP_200_OK)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    current_user: UserRead = Depends(require_catalog_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.update_material(db, material_id, payload)
    if material is None:
        if error == "invalid_location":
            raise not_found("LOCATION_NOT_FOUND", "Location not found")
        raise not_found("MATERIAL_NOT_FOUND", "Material not found")
    return material

@router.post("/{material_id}/archive", status_code=status.HTTP_200_OK)
def archive_material(
    material_id: int,
    reason: Annotated[
        str,
        Query(min_length=1, max_length=2_000, pattern=r".*\S.*"),
    ],
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> dict:
    success, error = service.archive_material(db, material_id, current_user.id, reason)
    if error == "not_found":
        raise not_found("MATERIAL_NOT_FOUND", "Material not found")
    if error == "active_reservation":
        raise conflict(
            "MATERIAL_HAS_ACTIVE_RESERVATION",
                "Material with an approved order or reserved stock cannot be archived; "
                "fulfill or cancel the order first"
        )
    if error == "already_archived":
        raise conflict("MATERIAL_ALREADY_ARCHIVED", "Material is already archived")
    if not success:
        raise bad_request("MATERIAL_ARCHIVE_FAILED", "Material could not be archived")
    return {"message": "Material archived successfully"}

@router.post("/{material_id}/restore", status_code=status.HTTP_200_OK)
def restore_material(
    material_id: int,
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> dict:
    success, error = service.restore_material(db, material_id, current_user.id)
    if error == "not_found":
        raise not_found("MATERIAL_NOT_FOUND", "Material not found")
    if error == "not_archived":
        raise conflict("MATERIAL_NOT_ARCHIVED", "Material is not archived")
    if not success:
        raise bad_request("MATERIAL_RESTORE_FAILED", "Material could not be restored")
    return {"message": "Material restored successfully"}    


@router.post("/{material_id}/adjust-quantity", response_model=MaterialRead)
def adjust_quantity(
    material_id: int,
    payload: QuantityAdjustment,
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.adjust_quantity(db, material_id, current_user.id, payload)
    if material is None:
        _raise_inventory_error(error)
    return material


@router.post("/{material_id}/check-in", response_model=MaterialRead)
def check_in_material(
    material_id: int,
    payload: QuantityChange,
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.check_in_material(db, material_id, current_user.id, payload)
    if material is None:
        _raise_inventory_error(error)
    return material


@router.post("/{material_id}/check-out", response_model=MaterialRead)
def check_out_material(
    material_id: int,
    payload: QuantityChange,
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.check_out_material(db, material_id, current_user.id, payload)
    if material is None:
        _raise_inventory_error(error)
    return material


@router.post("/{material_id}/move", response_model=MaterialRead)
def move_material(
    material_id: int,
    payload: MaterialMove,
    current_user: UserRead = Depends(require_inventory_manager),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.move_material(db, material_id, current_user.id, payload)
    if material is None:
        _raise_inventory_error(error)
    return material
