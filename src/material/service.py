from sqlalchemy import text
from sqlalchemy.orm import Session
from src.material.schemas import MaterialCreate, MaterialRead, MaterialUpdate

def list_materials(db: Session) -> list[MaterialRead]:
    rows = db.execute(
        text(
            """
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
                availability_status,
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
            """
        )
    ).mappings().all()

    return [MaterialRead(**row) for row in rows]

def get_material(db: Session, material_id: int) -> MaterialRead | None:
    row = db.execute(
        text(
            """
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
                availability_status,
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

def create_material(db: Session, payload: MaterialCreate) -> MaterialRead | None:
    existing_material = db.execute(
        text("SELECT id FROM materials WHERE material_code = :material_code"),
        {"material_code": payload.material_code},
    ).first()

    if existing_material is not None:
        return None

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

    return get_material(db, material_id)

def update_material(db: Session, material_id: int, payload: MaterialUpdate) -> MaterialRead | None:
    existing_material = db.execute(
        text("SELECT id FROM materials WHERE id = :material_id"),
        {"material_id": material_id},
    ).first()

    if existing_material is None:
        return None
    updates = {}

    if payload.material_name is not None:
        updates["material_name"] = payload.material_name
    if payload.qc_status is not None:
        updates["qc_status"] = payload.qc_status
    if payload.material_type is not None:
        updates["material_type"] = payload.material_type
    if payload.description is not None:
        updates["description"] = payload.description  
    if payload.source is not None:
        updates["source"] = payload.source
    if payload.unit is not None:
        updates["unit"] = payload.unit
    if payload.minimum_quantity is not None:
        updates["minimum_quantity"] = payload.minimum_quantity
    if payload.storage_condition is not None:
        updates["storage_condition"] = payload.storage_condition
    if payload.location_id is not None:
        updates["location_id"] = payload.location_id

    if not updates:
        return get_material(db, material_id)

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

    return get_material(db, material_id)

def archive_material(db: Session, material_id: int, current_user: int, reason: str) -> bool:
    existing_material = db.execute(
        text("SELECT id FROM materials WHERE id = :material_id"),
        {"material_id": material_id},
    ).first()

    if existing_material is None:
        return False

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
    db.commit()

    return True

def restore_material(db: Session, material_id: int) -> bool:
    existing_material = db.execute(
        text("SELECT id FROM materials WHERE id = :material_id"),
        {"material_id": material_id},
    ).first()

    if existing_material is None:
        return False
    
    db.execute(
        text(
            """
            UPDATE materials
            SET is_archived = FALSE, archived_at = NULL
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id},
    )
    db.commit()

    return True

def search_materials(
    db: Session,
    material_type: str | None = None,
    qc_status: str | None = None,
    availability_status: str | None = None,
    include_archived: bool = False,
) -> list[MaterialRead]:
    query = """
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
            availability_status,
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
        WHERE 1=1
    """

    if not include_archived:
        query += " AND is_archived = FALSE"

    if material_type:
        query += " AND material_type = :material_type"

    if qc_status:
        query += " AND qc_status = :qc_status"

    if availability_status:
        query += " AND availability_status = :availability_status"

    rows = db.execute(
        text(query),
        {
            "material_type": material_type,
            "qc_status": qc_status,
            "availability_status": availability_status,
        },
    ).mappings().all()

    return [MaterialRead(**row) for row in rows]






