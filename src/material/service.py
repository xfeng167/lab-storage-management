from sqlalchemy import text
from sqlalchemy.orm import Session
from src.core.pagination import Page, build_page, page_offset
from src.material.schemas import (
    MaterialCreate,
    MaterialMove,
    MaterialRead,
    MaterialUpdate,
    QuantityAdjustment,
    QuantityChange,
)


AVAILABILITY_STATUS_SQL = """
    CASE
        WHEN quantity_available - quantity_reserved <= 0 THEN 'unavailable'
        WHEN quantity_available - quantity_reserved <= minimum_quantity THEN 'low_stock'
        ELSE 'available'
    END
"""


def _location_exists(db: Session, location_id: int | None) -> bool:
    if location_id is None:
        return True

    location = db.execute(
        text("SELECT id FROM locations WHERE id = :location_id"),
        {"location_id": location_id},
    ).first()
    return location is not None


def _log_inventory_audit(
    db: Session,
    user_id: int,
    material_id: int,
    operation_type: str,
    before_value: str,
    after_value: str,
    reason: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO inventory_audit_logs (
                user_id,
                material_id,
                operation_type,
                before_value,
                after_value,
                reason
            )
            VALUES (
                :user_id,
                :material_id,
                :operation_type,
                :before_value,
                :after_value,
                :reason
            )
            """
        ),
        {
            "user_id": user_id,
            "material_id": material_id,
            "operation_type": operation_type,
            "before_value": before_value,
            "after_value": after_value,
            "reason": reason,
        },
    )


def list_materials(
    db: Session,
    page: int = 1,
    size: int = 25,
) -> Page[MaterialRead]:
    total = db.execute(
        text("SELECT COUNT(*) FROM materials WHERE is_archived = FALSE")
    ).scalar_one()
    rows = db.execute(
        text(
            f"""
            SELECT
                id,
                material_code,
                material_name,
                material_type,
                description,
                source,
                quantity_available,
                quantity_reserved,
                unit,
                minimum_quantity,
                {AVAILABILITY_STATUS_SQL} AS availability_status,
                qc_status,
                storage_condition,
                location_id,
                is_archived,
                archived_at,
                archived_by_user_id,
                archive_reason,
                created_at,
                updated_at
            FROM materials
            WHERE is_archived = FALSE
            ORDER BY id
            LIMIT :size OFFSET :offset
            """
        ),
        {"size": size, "offset": page_offset(page, size)},
    ).mappings().all()

    return build_page(
        [MaterialRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )


def adjust_quantity(
    db: Session,
    material_id: int,
    user_id: int,
    payload: QuantityAdjustment,
) -> tuple[MaterialRead | None, str | None]:
    row = db.execute(
        text(
            """
            SELECT quantity_available, quantity_reserved, is_archived
            FROM materials
            WHERE id = :material_id
            FOR UPDATE
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if row is None:
        return None, "not_found"
    if row["is_archived"]:
        return None, "archived"

    before_quantity = row["quantity_available"]
    after_quantity = payload.quantity_available
    if after_quantity < row["quantity_reserved"]:
        return None, "insufficient_quantity"

    db.execute(
        text(
            """
            UPDATE materials
            SET quantity_available = :quantity_available
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id, "quantity_available": after_quantity},
    )
    _log_inventory_audit(
        db,
        user_id,
        material_id,
        "adjust_quantity",
        str(before_quantity),
        str(after_quantity),
        payload.reason,
    )
    updated_material = get_material(db, material_id)
    db.commit()

    return updated_material, None


def check_in_material(
    db: Session,
    material_id: int,
    user_id: int,
    payload: QuantityChange,
) -> tuple[MaterialRead | None, str | None]:
    row = db.execute(
        text(
            """
            SELECT quantity_available, quantity_reserved, is_archived
            FROM materials
            WHERE id = :material_id
            FOR UPDATE
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if row is None:
        return None, "not_found"
    if row["is_archived"]:
        return None, "archived"

    before_quantity = row["quantity_available"]
    after_quantity = before_quantity + payload.quantity
    db.execute(
        text(
            """
            UPDATE materials
            SET quantity_available = :quantity_available
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id, "quantity_available": after_quantity},
    )
    _log_inventory_audit(
        db,
        user_id,
        material_id,
        "check_in",
        str(before_quantity),
        str(after_quantity),
        payload.reason,
    )
    updated_material = get_material(db, material_id)
    db.commit()

    return updated_material, None


def check_out_material(
    db: Session,
    material_id: int,
    user_id: int,
    payload: QuantityChange,
) -> tuple[MaterialRead | None, str | None]:
    row = db.execute(
        text(
            """
            SELECT quantity_available, quantity_reserved, is_archived
            FROM materials
            WHERE id = :material_id
            FOR UPDATE
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if row is None:
        return None, "not_found"
    if row["is_archived"]:
        return None, "archived"

    before_quantity = row["quantity_available"]
    after_quantity = before_quantity - payload.quantity
    if after_quantity < row["quantity_reserved"]:
        return None, "insufficient_quantity"

    db.execute(
        text(
            """
            UPDATE materials
            SET quantity_available = :quantity_available
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id, "quantity_available": after_quantity},
    )
    _log_inventory_audit(
        db,
        user_id,
        material_id,
        "check_out",
        str(before_quantity),
        str(after_quantity),
        payload.reason,
    )
    updated_material = get_material(db, material_id)
    db.commit()

    return updated_material, None


def move_material(
    db: Session,
    material_id: int,
    user_id: int,
    payload: MaterialMove,
) -> tuple[MaterialRead | None, str | None]:
    if not _location_exists(db, payload.location_id):
        return None, "invalid_location"

    row = db.execute(
        text("SELECT location_id, is_archived FROM materials WHERE id = :material_id"),
        {"material_id": material_id},
    ).mappings().first()

    if row is None:
        return None, "not_found"
    if row["is_archived"]:
        return None, "archived"

    before_location_id = row["location_id"]
    after_location_id = payload.location_id
    db.execute(
        text(
            """
            UPDATE materials
            SET location_id = :location_id
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id, "location_id": after_location_id},
    )
    _log_inventory_audit(
        db,
        user_id,
        material_id,
        "move",
        str(before_location_id),
        str(after_location_id),
        payload.reason,
    )
    db.commit()

    return get_material(db, material_id), None

def get_material(db: Session, material_id: int) -> MaterialRead | None:
    row = db.execute(
        text(
            f"""
            SELECT
                id,
                material_code,
                material_name,
                material_type,
                description,
                source,
                quantity_available,
                quantity_reserved,
                unit,
                minimum_quantity,
                {AVAILABILITY_STATUS_SQL} AS availability_status,
                qc_status,
                storage_condition,
                location_id,
                is_archived,
                archived_at,
                archived_by_user_id,
                archive_reason,
                created_at,
                updated_at
            FROM materials
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if row is None:
        return None

    return MaterialRead(**row)

def create_material(
    db: Session,
    payload: MaterialCreate,
) -> tuple[MaterialRead | None, str | None]:
    if not _location_exists(db, payload.location_id):
        return None, "invalid_location"

    existing_material = db.execute(
        text("SELECT id FROM materials WHERE material_code = :material_code"),
        {"material_code": payload.material_code},
    ).first()

    if existing_material is not None:
        return None, "duplicate_code"

    db.execute(
    text(
        """
        INSERT INTO materials (
            material_code,
            material_name,
            material_type,
            description,
            source,
            quantity_available,
            unit,
            minimum_quantity,
            qc_status,
            storage_condition,
            location_id
        )
        VALUES (
            :material_code,
            :material_name,
            :material_type,
            :description,
            :source,
            :quantity_available,
            :unit,
            :minimum_quantity,
            :qc_status,
            :storage_condition,
            :location_id
        )
        """
    ),
    {
        "material_code": payload.material_code,
        "material_name": payload.material_name,
        "material_type": payload.material_type,
        "description": payload.description,
        "source": payload.source,
        "quantity_available": payload.quantity_available,
        "unit": payload.unit,
        "minimum_quantity": payload.minimum_quantity,
        "qc_status": payload.qc_status,
        "storage_condition": payload.storage_condition,
        "location_id": payload.location_id,
        },
    )

    material_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()

    return get_material(db, material_id), None

def update_material(
    db: Session,
    material_id: int,
    payload: MaterialUpdate,
) -> tuple[MaterialRead | None, str | None]:
    existing_material = db.execute(
        text("SELECT id FROM materials WHERE id = :material_id"),
        {"material_id": material_id},
    ).first()

    if existing_material is None:
        return None, "not_found"
    if "location_id" in payload.model_fields_set and not _location_exists(db, payload.location_id):
        return None, "invalid_location"

    updates = {}
    editable_fields = {
        "material_name",
        "qc_status",
        "material_type",
        "description",
        "source",
        "unit",
        "minimum_quantity",
        "storage_condition",
        "location_id",
    }

    for field in editable_fields:
        if field in payload.model_fields_set:
            updates[field] = getattr(payload, field)

    if not updates:
        return get_material(db, material_id), None

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    db.execute(
        text(
            f"""
            UPDATE materials
            SET {set_clause}
            WHERE id = :material_id
            """
        ),
        {**updates, "material_id": material_id},
    )
    
    db.commit()

    return get_material(db, material_id), None

def archive_material(
    db: Session,
    material_id: int,
    current_user: int,
    reason: str,
) -> tuple[bool, str | None]:
    existing_material = db.execute(
        text(
            """
            SELECT id, is_archived, quantity_reserved
            FROM materials
            WHERE id = :material_id
            FOR UPDATE
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if existing_material is None:
        return False, "not_found"
    if existing_material["is_archived"]:
        return False, "already_archived"

    approved_order_exists = db.execute(
        text(
            """
            SELECT id
            FROM orders
            WHERE material_id = :material_id
            AND status = 'approved'
            LIMIT 1
            """
        ),
        {"material_id": material_id},
    ).first()
    if existing_material["quantity_reserved"] > 0:
        return False, "active_reservation"
    if approved_order_exists is not None:
        return False, "active_reservation"

    db.execute(
        text(
            """
            UPDATE materials
            SET is_archived = TRUE, archived_at = CURRENT_TIMESTAMP, archived_by_user_id = :current_user, archive_reason = :reason
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id, "current_user": current_user, "reason": reason},
    )
    _log_inventory_audit(
        db,
        current_user,
        material_id,
        "archive_material",
        "active",
        "archived",
        reason,
    )
    db.commit()

    return True, None


def restore_material(
    db: Session,
    material_id: int,
    current_user: int,
) -> tuple[bool, str | None]:
    existing_material = db.execute(
        text(
            """
            SELECT id, is_archived, archive_reason
            FROM materials
            WHERE id = :material_id
            FOR UPDATE
            """
        ),
        {"material_id": material_id},
    ).mappings().first()

    if existing_material is None:
        return False, "not_found"
    if not existing_material["is_archived"]:
        return False, "not_archived"

    db.execute(
        text(
            """
            UPDATE materials
            SET
                is_archived = FALSE,
                archived_at = NULL,
                archived_by_user_id = NULL,
                archive_reason = NULL
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id},
    )
    previous_reason = existing_material["archive_reason"]
    restore_reason = "Material restored"
    if previous_reason:
        restore_reason += f"; previous archive reason: {previous_reason}"
    _log_inventory_audit(
        db,
        current_user,
        material_id,
        "restore_material",
        "archived",
        "active",
        restore_reason,
    )
    db.commit()

    return True, None

def search_materials(
    db: Session,
    keyword: str | None = None,
    material_type: str | None = None,
    source: str | None = None,
    qc_status: str | None = None,
    availability_status: str | None = None,
    location_id: int | None = None,
    low_stock: bool = False,
    include_archived: bool = False,
    page: int = 1,
    size: int = 25,
) -> Page[MaterialRead]:
    query = f"""
        SELECT
            id,
            material_code,
            material_name,
            material_type,
            description,
            source,
            quantity_available,
            quantity_reserved,
            unit,
            minimum_quantity,
            {AVAILABILITY_STATUS_SQL} AS availability_status,
            qc_status,
            storage_condition,
            location_id,
            is_archived,
            archived_at,
            archived_by_user_id,
            archive_reason,
            created_at,
            updated_at
        FROM materials
    """
    params: dict[str, object] = {}
    conditions = ["1=1"]

    if not include_archived:
        conditions.append("is_archived = FALSE")

    if keyword:
        conditions.append(
            """
            (
                material_code LIKE :keyword
                OR material_name LIKE :keyword
                OR description LIKE :keyword
            )
            """
        )
        params["keyword"] = f"%{keyword}%"

    if material_type:
        conditions.append("material_type = :material_type")
        params["material_type"] = material_type

    if source:
        conditions.append("source = :source")
        params["source"] = source

    if qc_status:
        conditions.append("qc_status = :qc_status")
        params["qc_status"] = qc_status

    if availability_status == "available":
        conditions.append("quantity_available - quantity_reserved > minimum_quantity")
    elif availability_status == "low_stock":
        conditions.append("quantity_available - quantity_reserved > 0")
        conditions.append(
            "quantity_available - quantity_reserved <= minimum_quantity"
        )
    elif availability_status == "unavailable":
        conditions.append("quantity_available - quantity_reserved <= 0")
    elif availability_status:
        return build_page([], page=page, size=size, total=0)

    if location_id is not None:
        conditions.append("location_id = :location_id")
        params["location_id"] = location_id

    if low_stock:
        conditions.append(
            "quantity_available - quantity_reserved <= minimum_quantity"
        )

    where_clause = " AND ".join(conditions)
    query += f" WHERE {where_clause}"
    total = db.execute(
        text(f"SELECT COUNT(*) FROM materials WHERE {where_clause}"),
        params,
    ).scalar_one()
    query += " ORDER BY id LIMIT :size OFFSET :offset"

    rows = db.execute(
        text(query),
        {**params, "size": size, "offset": page_offset(page, size)},
    ).mappings().all()

    return build_page(
        [MaterialRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )
