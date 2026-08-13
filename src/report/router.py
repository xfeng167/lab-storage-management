from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.auth.dependencies import require_report_reader
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
    current_user: UserRead = Depends(require_report_reader),
    db: Session = Depends(get_db),
) -> list[LowStockMaterialRead]:
    return service.list_low_stock_materials(db)


@router.get("/pending-orders", response_model=list[PendingOrderRead])
def list_pending_orders(
    current_user: UserRead = Depends(require_report_reader),
    db: Session = Depends(get_db),
) -> list[PendingOrderRead]:
    return service.list_pending_orders(db)


@router.get(
    "/recent-inventory-activity",
    response_model=list[RecentInventoryActivityRead],
    description=(
        "Staff/admin reporting view over inventory audit history, including "
        "order reservation, fulfillment, and reservation-release activity. "
        "Results are newest first and capped at 100 records."
    ),
)
def list_recent_inventory_activity(
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserRead = Depends(require_report_reader),
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
    current_user: UserRead = Depends(require_report_reader),
    db: Session = Depends(get_db),
) -> list[MaterialsByLocationRead]:
    return service.list_materials_by_location(db)
