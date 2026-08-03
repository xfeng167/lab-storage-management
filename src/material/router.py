from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, require_staff_user
from src.db.connection import get_db
from src.material import service
from src.material.schemas import MaterialCreate, MaterialRead, MaterialUpdate
from src.user.schemas import UserRead

router = APIRouter()

@router.get("", response_model=list[MaterialRead])
def list_materials(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaterialRead]:
    return service.list_materials(db)

@router.get("/search", response_model=list[MaterialRead])
def search_materials(
    material_type: str | None = None,
    qc_status: str | None = None,
    availability_status: str | None = None,
    include_archived: bool = False,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaterialRead]:
    return service.search_materials(
        db, material_type, qc_status, availability_status, include_archived
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
    current_user: UserRead = Depends(require_staff_user),
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
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> dict:
    success = service.restore_material(db, material_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return {"message": "Material restored successfully"}    


