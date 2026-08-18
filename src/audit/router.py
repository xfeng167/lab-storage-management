from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.audit import service
from src.audit.schemas import InventoryAuditLogRead
from src.auth.dependencies import require_audit_reader
from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from src.db.connection import get_db
from src.user.schemas import UserRead

router = APIRouter()


@router.get(
    "/audit-logs",
    response_model=Page[InventoryAuditLogRead],
    description=(
        "Admin-only, paginated inventory audit history. Order approval, "
        "fulfillment, and approved-order cancellation appear here with their "
        "before/after inventory snapshots."
    ),
)
def list_inventory_audit_logs(
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_audit_reader),
    db: Session = Depends(get_db),
) -> Page[InventoryAuditLogRead]:
    return service.list_inventory_audit_logs(
        db,
        user_id=user_id,
        material_id=material_id,
        operation_type=operation_type,
        page=page,
        size=size,
    )
