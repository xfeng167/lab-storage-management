from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


ORDER_ARCHIVE_COLUMNS = {
    "is_archived": "ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE",
    "archived_at": "ADD COLUMN archived_at TIMESTAMP NULL",
    "archived_by_user_id": "ADD COLUMN archived_by_user_id INT NULL",
    "archive_reason": "ADD COLUMN archive_reason TEXT",
}

USER_PROFILE_COLUMNS = {
    "profile_picture": "ADD COLUMN profile_picture MEDIUMTEXT NULL",
}


def ensure_database_schema(engine: Engine) -> None:
    ensure_missing_columns(engine, "users", USER_PROFILE_COLUMNS)
    ensure_missing_columns(engine, "orders", ORDER_ARCHIVE_COLUMNS)


def ensure_missing_columns(engine: Engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    missing_columns = [
        column_definition
        for column_name, column_definition in columns.items()
        if column_name not in existing_columns
    ]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column_definition in missing_columns:
            connection.execute(text(f"ALTER TABLE {table_name} {column_definition}"))
