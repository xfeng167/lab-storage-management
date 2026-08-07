from sqlalchemy import text
from sqlalchemy.orm import Session
from src.audit.schemas import InventoryAuditLogRead

def list_inventory_audit_logs(
    db: Session,
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
) -> list[InventoryAuditLogRead]:
    query = """
        SELECT
            id,
            user_id,
            material_id,
            operation_type,
            before_value,
            after_value,
            reason,
            created_at
        FROM inventory_audit_logs
        WHERE 1=1
    """

    if user_id is not None:
        query += " AND user_id = :user_id"
    if material_id is not None:
        query += " AND material_id = :material_id"
    if operation_type is not None:
        query += " AND operation_type = :operation_type"

    query += " ORDER BY created_at DESC, id DESC"

    rows = db.execute(
        text(query),
        {
            "user_id": user_id,
            "material_id": material_id,
            "operation_type": operation_type,
        },
    ).mappings().all()

    return [InventoryAuditLogRead(**row) for row in rows]
