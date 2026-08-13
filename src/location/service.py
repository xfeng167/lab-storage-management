from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.pagination import Page, build_page, page_offset
from src.location.schemas import LocationCreate, LocationRead, LocationUpdate

LOCATION_SELECT = """
    SELECT
        id,
        name,
        location_type,
        parent_location_id,
        temperature_zone,
        description,
        created_at,
        updated_at
    FROM locations
"""

LOCATION_HIERARCHY_LOCK = "location_hierarchy"


def _acquire_hierarchy_lock(db: Session) -> bool:
    return db.execute(
        text(
            """
            SELECT lock_name
            FROM application_locks
            WHERE lock_name = :lock_name
            FOR UPDATE
            """
        ),
        {"lock_name": LOCATION_HIERARCHY_LOCK},
    ).scalar_one_or_none() is not None


def _release_hierarchy_lock(db: Session) -> None:
    # Successful helpers commit the transaction. Validation failures reach
    # this function with the lock row still held and must roll back promptly.
    if db.in_transaction():
        db.rollback()

def _parent_location_error(
    db: Session,
    parent_location_id: int | None,
    current_location_id: int | None = None,
) -> str | None:
    if parent_location_id is None:
        return None
    if parent_location_id == current_location_id:
        return "cycle"

    parent_location = db.execute(
        text(
            """
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_location_id
                FROM locations
                WHERE id = :parent_location_id

                UNION DISTINCT

                SELECT locations.id, locations.parent_location_id
                FROM locations
                JOIN ancestors ON locations.id = ancestors.parent_location_id
            )
            SELECT id FROM ancestors
            """
        ),
        {"parent_location_id": parent_location_id},
    ).scalars().all()
    if not parent_location:
        return "parent_not_found"
    if current_location_id in parent_location:
        return "cycle"
    return None


def list_locations(
    db: Session,
    page: int = 1,
    size: int = 25,
) -> Page[LocationRead]:
    total = db.execute(text("SELECT COUNT(*) FROM locations")).scalar_one()
    rows = db.execute(
        text(f"{LOCATION_SELECT} ORDER BY id LIMIT :size OFFSET :offset"),
        {"size": size, "offset": page_offset(page, size)},
    ).mappings().all()
    return build_page(
        [LocationRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )


def get_location(db: Session, location_id: int) -> LocationRead | None:
    row = db.execute(
        text(f"{LOCATION_SELECT} WHERE id = :location_id"),
        {"location_id": location_id},
    ).mappings().first()

    if row is None:
        return None

    return LocationRead(**row)


def _create_location_locked(
    db: Session,
    payload: LocationCreate,
) -> tuple[LocationRead | None, str | None]:
    parent_error = _parent_location_error(db, payload.parent_location_id)
    if parent_error is not None:
        return None, parent_error

    db.execute(
        text(
            """
            INSERT INTO locations (
                name,
                location_type,
                parent_location_id,
                temperature_zone,
                description
            )
            VALUES (
                :name,
                :location_type,
                :parent_location_id,
                :temperature_zone,
                :description
            )
            """
        ),
        {
            "name": payload.name,
            "location_type": payload.location_type,
            "parent_location_id": payload.parent_location_id,
            "temperature_zone": payload.temperature_zone,
            "description": payload.description,
        },
    )
    location_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()

    return get_location(db, location_id), None


def _update_location_locked(
    db: Session,
    location_id: int,
    payload: LocationUpdate,
) -> tuple[LocationRead | None, str | None]:
    existing_location = db.execute(
        text("SELECT id FROM locations WHERE id = :location_id"),
        {"location_id": location_id},
    ).first()

    if existing_location is None:
        return None, "not_found"
    if "parent_location_id" in payload.model_fields_set:
        parent_error = _parent_location_error(
            db,
            payload.parent_location_id,
            location_id,
        )
        if parent_error is not None:
            return None, parent_error

    updates = {}
    editable_fields = {
        "name",
        "location_type",
        "parent_location_id",
        "temperature_zone",
        "description",
    }

    for field in editable_fields:
        if field in payload.model_fields_set:
            updates[field] = getattr(payload, field)

    if not updates:
        return get_location(db, location_id), None

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    db.execute(
        text(
            f"""
            UPDATE locations
            SET {set_clause}
            WHERE id = :location_id
            """
        ),
        {**updates, "location_id": location_id},
    )
    db.commit()

    return get_location(db, location_id), None


def create_location(
    db: Session,
    payload: LocationCreate,
) -> tuple[LocationRead | None, str | None]:
    if not _acquire_hierarchy_lock(db):
        return None, "hierarchy_busy"
    try:
        return _create_location_locked(db, payload)
    finally:
        _release_hierarchy_lock(db)


def update_location(
    db: Session,
    location_id: int,
    payload: LocationUpdate,
) -> tuple[LocationRead | None, str | None]:
    if not _acquire_hierarchy_lock(db):
        return None, "hierarchy_busy"
    try:
        return _update_location_locked(db, location_id, payload)
    finally:
        _release_hierarchy_lock(db)
