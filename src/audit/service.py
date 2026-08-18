from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.pagination import Page, build_page, page_offset
from src.audit.schemas import InventoryAuditLogRead

def list_inventory_audit_logs(
    db: Session,
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    page: int = 1,
    size: int = 25,
) -> Page[InventoryAuditLogRead]:
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

    conditions = []
    params: dict[str, object] = {}

    if user_id is not None:
        conditions.append("user_id = :user_id")
        params["user_id"] = user_id
    if material_id is not None:
        conditions.append("material_id = :material_id")
        params["material_id"] = material_id
    if operation_type is not None:
        conditions.append("operation_type = :operation_type")
        params["operation_type"] = operation_type

    if conditions:
        query += " AND " + " AND ".join(conditions)

    total = db.execute(
        text(
            "SELECT COUNT(*) FROM inventory_audit_logs WHERE 1=1"
            + (" AND " + " AND ".join(conditions) if conditions else "")
        ),
        params,
    ).scalar_one()

    query += " ORDER BY created_at DESC, id DESC LIMIT :size OFFSET :offset"

    rows = db.execute(
        text(query),
        {**params, "size": size, "offset": page_offset(page, size)},
    ).mappings().all()

    return build_page(
        [InventoryAuditLogRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )
