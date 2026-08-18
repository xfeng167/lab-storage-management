from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must identify a dedicated test database; see docs/development.md"
    )

test_database_url = make_url(TEST_DATABASE_URL)
if not test_database_url.database or "test" not in test_database_url.database.lower():
    raise RuntimeError("TEST_DATABASE_URL database name must contain 'test'")
if test_database_url.username == "root":
    raise RuntimeError("Tests must not connect with the MySQL root account")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

TABLES_TO_CLEAN = [
    "login_throttle",
    "inventory_audit_logs",
    "orders",
    "token_table",
    "materials",
    "locations",
    "users",
]


def _alembic_config() -> Config:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "migrations"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    return config


def _reset_test_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table_name in inspect(connection).get_table_names():
            escaped_table_name = table_name.replace("`", "``")
            connection.execute(text(f"DROP TABLE `{escaped_table_name}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    command.upgrade(_alembic_config(), "head")


def _clean_test_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table_name in TABLES_TO_CLEAN:
            connection.execute(text(f"TRUNCATE TABLE `{table_name}`"))
        connection.execute(
            text(
                """
                INSERT IGNORE INTO application_locks (lock_name)
                VALUES ('location_hierarchy')
                """
            )
        )
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        _reset_test_schema(engine)
        _clean_test_tables(engine)
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_database_between_tests() -> None:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        _clean_test_tables(engine)
    finally:
        engine.dispose()
