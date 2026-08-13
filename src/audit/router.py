from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.audit import service
from src.audit.schemas import InventoryAuditLogRead
from src.auth.dependencies import require_admin_user
from src.db.connection import get_db
from src.user.schemas import UserRead

router = APIRouter()


@router.get("/audit-logs", response_model=list[InventoryAuditLogRead])
def list_inventory_audit_logs(
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[InventoryAuditLogRead]:
    return service.list_inventory_audit_logs(
        db,
        user_id=user_id,
        material_id=material_id,
        operation_type=operation_type,
    )
