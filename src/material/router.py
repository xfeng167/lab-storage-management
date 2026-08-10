from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, require_staff_user, require_admin_user
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    if error == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived material cannot be changed",
        )
    if error == "insufficient_quantity":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient quantity available",
        )
    if error == "invalid_location":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid location",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Inventory operation failed",
    )

@router.get("", response_model=list[MaterialRead])
def list_materials(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaterialRead]:
    return service.list_materials(db)

@router.get("/search", response_model=list[MaterialRead])
def search_materials(
    keyword: str | None = None,
    material_type: str | None = None,
    source: str | None = None,
    qc_status: str | None = None,
    availability_status: str | None = None,
    location_id: int | None = None,
    low_stock: bool = False,
    include_archived: bool = False,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaterialRead]:
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
    )

@router.get("/{material_id}", response_model=MaterialRead)
def get_material(
    material_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = service.get_material(db, material_id)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return material

@router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = service.create_material(db, payload)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Material creation failed",
        )
    return material

@router.patch("/{material_id}", status_code=status.HTTP_200_OK)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material = service.update_material(db, material_id, payload)
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return material

@router.post("/{material_id}/archive", status_code=status.HTTP_200_OK)
def archive_material(
    material_id: int,
    reason: str,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    success = service.archive_material(db, material_id, current_user.id, reason)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return {"message": "Material archived successfully"}

@router.post("/{material_id}/restore", status_code=status.HTTP_200_OK)
def restore_material(
    material_id: int,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    success = service.restore_material(db, material_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return {"message": "Material restored successfully"}    


@router.post("/{material_id}/adjust-quantity", response_model=MaterialRead)
def adjust_quantity(
    material_id: int,
    payload: QuantityAdjustment,
    current_user: UserRead = Depends(require_admin_user),
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
    current_user: UserRead = Depends(require_admin_user),
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
    current_user: UserRead = Depends(require_admin_user),
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
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> MaterialRead:
    material, error = service.move_material(db, material_id, current_user.id, payload)
    if material is None:
        _raise_inventory_error(error)
    return material
