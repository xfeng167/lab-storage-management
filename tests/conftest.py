import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


TEST_DATABASE_NAME = "lab_storage_test_db"
TEST_DATABASE_URL = (
    f"mysql+pymysql://lab_user:lab_password@localhost:3306/{TEST_DATABASE_NAME}"
)
ROOT_DATABASE_URL = "mysql+pymysql://root:root_password@localhost:3306/mysql"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL


TABLE_DEFINITIONS = [
    """
    CREATE TABLE IF NOT EXISTS test_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(80) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'viewer',
        profile_picture MEDIUMTEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS token_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        token VARCHAR(255) NOT NULL UNIQUE,
        user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS locations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        location_type VARCHAR(80) NOT NULL,
        parent_location_id INT NULL,
        temperature_zone VARCHAR(80),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS materials (
        id INT AUTO_INCREMENT PRIMARY KEY,
        material_code VARCHAR(80) NOT NULL UNIQUE,
        material_name VARCHAR(255) NOT NULL,
        material_type VARCHAR(80) NOT NULL,
        description TEXT,
        source VARCHAR(255),
        quantity_available INT NOT NULL DEFAULT 0,
        quantity_reserved INT NOT NULL DEFAULT 0,
        unit VARCHAR(40) NOT NULL,
        minimum_quantity INT NOT NULL DEFAULT 0,
        availability_status VARCHAR(40) NOT NULL DEFAULT 'available',
        qc_status VARCHAR(40) NOT NULL DEFAULT 'pending',
        storage_condition VARCHAR(120),
        location_id INT,
        is_archived BOOLEAN NOT NULL DEFAULT FALSE,
        archived_at TIMESTAMP NULL,
        archived_by_user_id INT NULL,
        archive_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory_audit_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        material_id INT NOT NULL,
        operation_type VARCHAR(80) NOT NULL,
        before_value VARCHAR(255) NOT NULL,
        after_value VARCHAR(255) NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        requested_by_user_id INT NOT NULL,
        material_id INT NOT NULL,
        requested_quantity INT NOT NULL,
        reserved_quantity INT NOT NULL DEFAULT 0,
        status VARCHAR(40) NOT NULL DEFAULT 'submitted',
        request_notes TEXT,
        reviewed_by_user_id INT NULL,
        reviewed_at TIMESTAMP NULL,
        outcome_notes TEXT,
        is_archived BOOLEAN NOT NULL DEFAULT FALSE,
        archived_at TIMESTAMP NULL,
        archived_by_user_id INT NULL,
        archive_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (requested_by_user_id) REFERENCES users(id),
        FOREIGN KEY (material_id) REFERENCES materials(id),
        FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id)
    )
    """,
]

TABLES_TO_CLEAN = [
    "inventory_audit_logs",
    "orders",
    "token_table",
    "materials",
    "locations",
    "users",
    "test_table",
]


def _create_test_database() -> None:
    root_engine = create_engine(ROOT_DATABASE_URL, pool_pre_ping=True)
    with root_engine.begin() as connection:
        connection.execute(
            text(f"CREATE DATABASE IF NOT EXISTS {TEST_DATABASE_NAME}")
        )
        connection.execute(
            text(
                f"GRANT ALL PRIVILEGES ON {TEST_DATABASE_NAME}.* "
                "TO 'lab_user'@'%'"
            )
        )
    root_engine.dispose()


def _create_test_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        for table_definition in TABLE_DEFINITIONS:
            connection.execute(text(table_definition))
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN profile_picture MEDIUMTEXT NULL"))
        except Exception:
            pass
        for column_definition in [
            "ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE",
            "ADD COLUMN archived_at TIMESTAMP NULL",
            "ADD COLUMN archived_by_user_id INT NULL",
            "ADD COLUMN archive_reason TEXT",
        ]:
            try:
                connection.execute(text(f"ALTER TABLE orders {column_definition}"))
            except Exception:
                pass


def _clean_test_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table_name in TABLES_TO_CLEAN:
            connection.execute(text(f"TRUNCATE TABLE {table_name}"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    _create_test_database()
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    _create_test_tables(engine)
    _clean_test_tables(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database_between_tests() -> None:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    _clean_test_tables(engine)
    engine.dispose()
