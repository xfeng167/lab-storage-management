from sqlalchemy import text
from sqlalchemy.orm import Session

from src.test_table.schemas import TestTableCreate, TestTableRead, TestTableUpdate


def _get_table_columns(db: Session) -> set[str]:
    rows = db.execute(text("SHOW COLUMNS FROM test_table")).mappings().all()
    return {row["Field"] for row in rows}


def list_items(db: Session) -> list[TestTableRead]:
    rows = db.execute(text("SELECT id, name FROM test_table ORDER BY id")).mappings().all()
    return [TestTableRead(**row) for row in rows]


def create_item(db: Session, payload: TestTableCreate) -> TestTableRead:
    columns = _get_table_columns(db)
    insert_columns = ["name"]
    insert_values = [":name"]
    params = {"name": payload.name}

    if "created_at" in columns:
        insert_columns.append("created_at")
        insert_values.append("NOW()")
    if "updated_at" in columns:
        insert_columns.append("updated_at")
        insert_values.append("NOW()")

    db.execute(
        text(
            f"""
            INSERT INTO test_table ({", ".join(insert_columns)})
            VALUES ({", ".join(insert_values)})
            """
        ),
        params,
    )
    item_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()
    return TestTableRead(id=item_id, name=payload.name)


def update_item(db: Session, item_id: int, payload: TestTableUpdate) -> TestTableRead | None:
    columns = _get_table_columns(db)
    set_clause = "name = :name"
    if "updated_at" in columns:
        set_clause += ", updated_at = NOW()"

    result = db.execute(
        text(f"UPDATE test_table SET {set_clause} WHERE id = :id"),
        {"id": item_id, "name": payload.name},
    )
    if result.rowcount == 0:
        db.rollback()
        return None

    db.commit()
    return TestTableRead(id=item_id, name=payload.name)


def delete_item(db: Session, item_id: int) -> bool:
    result = db.execute(text("DELETE FROM test_table WHERE id = :id"), {"id": item_id})
    if result.rowcount == 0:
        db.rollback()
        return False

    db.commit()
    return True
