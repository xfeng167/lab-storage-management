from sqlalchemy import text
from sqlalchemy.orm import Session

from src.report.schemas import (
    LowStockMaterialRead,
    MaterialsByLocationRead,
    PendingOrderRead,
    RecentInventoryActivityRead,
)


def list_low_stock_materials(db: Session) -> list[LowStockMaterialRead]:
    rows = db.execute(
        text(
            """
            SELECT
                id,
                material_code,
                material_name,
                quantity_available,
                quantity_reserved,
                minimum_quantity,
                unit,
                location_id
            FROM materials
            WHERE is_archived = FALSE
            AND quantity_available - quantity_reserved <= minimum_quantity
            ORDER BY quantity_available - quantity_reserved ASC, material_name ASC
            """
        )
    ).mappings().all()

    return [LowStockMaterialRead(**row) for row in rows]


def list_pending_orders(db: Session) -> list[PendingOrderRead]:
    rows = db.execute(
        text(
            """
            SELECT
                orders.id,
                orders.requested_by_user_id,
                users.username AS requested_by_username,
                orders.material_id,
                materials.material_code,
                materials.material_name,
                materials.unit,
                orders.requested_quantity,
                orders.status,
                orders.request_notes,
                orders.created_at
            FROM orders
            JOIN users ON users.id = orders.requested_by_user_id
            JOIN materials ON materials.id = orders.material_id
            WHERE orders.status = 'submitted'
            ORDER BY orders.created_at ASC, orders.id ASC
            """
        )
    ).mappings().all()

    return [PendingOrderRead(**row) for row in rows]


def list_recent_inventory_activity(
    db: Session,
    user_id: int | None = None,
    material_id: int | None = None,
    operation_type: str | None = None,
    limit: int = 20,
) -> list[RecentInventoryActivityRead]:
    query = """
            SELECT
                inventory_audit_logs.id,
                inventory_audit_logs.user_id,
                users.username,
                inventory_audit_logs.material_id,
                materials.material_code,
                materials.material_name,
                inventory_audit_logs.operation_type,
                inventory_audit_logs.before_value,
                inventory_audit_logs.after_value,
                inventory_audit_logs.reason,
                inventory_audit_logs.created_at
            FROM inventory_audit_logs
            JOIN users ON users.id = inventory_audit_logs.user_id
            JOIN materials ON materials.id = inventory_audit_logs.material_id
            WHERE 1=1
    """
    params = {"limit": limit}

    if user_id is not None:
        query += " AND inventory_audit_logs.user_id = :user_id"
        params["user_id"] = user_id

    if material_id is not None:
        query += " AND inventory_audit_logs.material_id = :material_id"
        params["material_id"] = material_id

    if operation_type is not None:
        query += " AND inventory_audit_logs.operation_type = :operation_type"
        params["operation_type"] = operation_type

    query += """
            ORDER BY inventory_audit_logs.created_at DESC, inventory_audit_logs.id DESC
            LIMIT :limit
    """

    rows = db.execute(text(query), params).mappings().all()

    return [RecentInventoryActivityRead(**row) for row in rows]


def list_materials_by_location(db: Session) -> list[MaterialsByLocationRead]:
    rows = db.execute(
        text(
            """
            SELECT
                materials.location_id,
                COALESCE(locations.name, 'Unassigned') AS location_name,
                COUNT(materials.id) AS material_count,
                COALESCE(SUM(materials.quantity_available), 0) AS total_quantity_available,
                COALESCE(SUM(materials.quantity_reserved), 0) AS total_quantity_reserved
            FROM materials
            LEFT JOIN locations ON locations.id = materials.location_id
            WHERE materials.is_archived = FALSE
            GROUP BY materials.location_id, locations.name
            ORDER BY location_name ASC
            """
        )
    ).mappings().all()

    return [MaterialsByLocationRead(**row) for row in rows]
