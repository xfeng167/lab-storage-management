from sqlalchemy import text
from sqlalchemy.orm import Session
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

def _parent_location_is_valid(
    db: Session,
    parent_location_id: int | None,
    current_location_id: int | None = None,
) -> bool:
    if parent_location_id is None:
        return True
    if parent_location_id == current_location_id:
        return False

    parent_location = db.execute(
        text("SELECT id FROM locations WHERE id = :parent_location_id"),
        {"parent_location_id": parent_location_id},
    ).first()
    return parent_location is not None


def list_locations(db: Session) -> list[LocationRead]:
    rows = db.execute(text(f"{LOCATION_SELECT} ORDER BY id")).mappings().all()
    return [LocationRead(**row) for row in rows]


def get_location(db: Session, location_id: int) -> LocationRead | None:
    row = db.execute(
        text(f"{LOCATION_SELECT} WHERE id = :location_id"),
        {"location_id": location_id},
    ).mappings().first()

    if row is None:
        return None

    return LocationRead(**row)


def create_location(db: Session, payload: LocationCreate) -> LocationRead | None:
    if not _parent_location_is_valid(db, payload.parent_location_id):
        return None

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

    return get_location(db, location_id)


def update_location(
    db: Session,
    location_id: int,
    payload: LocationUpdate,
) -> LocationRead | None:
    existing_location = db.execute(
        text("SELECT id FROM locations WHERE id = :location_id"),
        {"location_id": location_id},
    ).first()

    if existing_location is None:
        return None
    if (
        "parent_location_id" in payload.model_fields_set
        and not _parent_location_is_valid(db, payload.parent_location_id, location_id)
    ):
        return None

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
        return get_location(db, location_id)

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

    return get_location(db, location_id)
