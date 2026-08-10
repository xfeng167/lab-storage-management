from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth.dependencies import require_staff_user
from src.db.connection import get_db
from src.report import service
from src.report.schemas import (
    LowStockMaterialRead,
    MaterialsByLocationRead,
    PendingOrderRead,
    RecentInventoryActivityRead,
)
from src.user.schemas import UserRead

router = APIRouter()


@router.get("/low-stock", response_model=list[LowStockMaterialRead])
def list_low_stock_materials(
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> list[LowStockMaterialRead]:
    return service.list_low_stock_materials(db)


@router.get("/pending-orders", response_model=list[PendingOrderRead])
def list_pending_orders(
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> list[PendingOrderRead]:
    return service.list_pending_orders(db)


@router.get("/recent-inventory-activity", response_model=list[RecentInventoryActivityRead])
def list_recent_inventory_activity(
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    limit: int = 20,
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> list[RecentInventoryActivityRead]:
    return service.list_recent_inventory_activity(
        db,
        user_id=user_id,
        material_id=material_id,
        operation_type=operation_type,
        limit=limit,
    )


@router.get("/materials-by-location", response_model=list[MaterialsByLocationRead])
def list_materials_by_location(
    current_user: UserRead = Depends(require_staff_user),
    db: Session = Depends(get_db),
) -> list[MaterialsByLocationRead]:
    return service.list_materials_by_location(db)
