from pathlib import Path

import pytest
from alembic import command
from alembic.migration import MigrationContext
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from src.db.connection import engine


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _script_config() -> Config:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "migrations"))
    return config


def test_database_is_at_the_latest_migration() -> None:
    expected_head = ScriptDirectory.from_config(_script_config()).get_current_head()
    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()

    assert current_revision == expected_head


def test_migrations_create_indexes_and_constraints() -> None:
    inspector = inspect(engine)

    assert "test_table" not in inspector.get_table_names()
    assert "login_throttle" in inspector.get_table_names()
    assert "application_locks" in inspector.get_table_names()
    assert "ix_token_table_created_at" in {
        index["name"] for index in inspector.get_indexes("token_table")
    }
    assert "availability_status" not in {
        column["name"] for column in inspector.get_columns("materials")
    }
    assert "ix_materials_active_search" in {
        index["name"] for index in inspector.get_indexes("materials")
    }
    assert "uq_materials_material_code" in {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("materials")
    }
    assert {
        "ck_materials_nonnegative_quantities",
        "ck_materials_reserved_within_available",
        "ck_materials_qc_status",
    }.issubset({
        constraint["name"]
        for constraint in inspector.get_check_constraints("materials")
    })
    assert {
        "ck_orders_status",
        "ck_orders_positive_requested_quantity",
        "ck_orders_nonnegative_reserved_quantity",
        "ck_orders_reserved_within_requested",
        "ck_orders_reservation_matches_status",
    }.issubset({
        constraint["name"]
        for constraint in inspector.get_check_constraints("orders")
    })
    assert {
        "ix_orders_status",
        "ix_orders_requester_archived_status_id",
        "ix_orders_material_status",
    }.issubset({index["name"] for index in inspector.get_indexes("orders")})
    assert {
        "ix_inventory_audit_logs_created_at",
        "ix_inventory_audit_logs_material_created_at",
        "ix_inventory_audit_logs_user_created_at",
        "ix_inventory_audit_logs_operation_created_at",
    }.issubset({
        index["name"] for index in inspector.get_indexes("inventory_audit_logs")
    })
    assert (
        ("parent_location_id",),
        "locations",
        ("id",),
    ) in {
        (
            tuple(constraint["constrained_columns"]),
            constraint["referred_table"],
            tuple(constraint["referred_columns"]),
        )
        for constraint in inspector.get_foreign_keys("locations")
    }
    assert all(
        constraint.get("options", {}).get("ondelete") == "RESTRICT"
        for table_name in (
            "token_table",
            "locations",
            "materials",
            "orders",
            "inventory_audit_logs",
        )
        for constraint in inspector.get_foreign_keys(table_name)
    )


def test_database_rejects_invalid_domain_values_and_relationships() -> None:
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO materials (
                    material_code,
                    material_name,
                    material_type,
                    quantity_available,
                    unit,
                    minimum_quantity,
                    qc_status
                )
                VALUES ('INVALID-STOCK', 'Invalid', 'test', -1, 'each', 0, 'pending')
                """
            )
        )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES ('constraint_user', 'constraint@example.com', 'hash', 'viewer')
                """
            )
        )
        user_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO materials (
                    material_code,
                    material_name,
                    material_type,
                    quantity_available,
                    unit,
                    minimum_quantity,
                    qc_status
                )
                VALUES ('CONSTRAINT-MATERIAL', 'Constraint material', 'test', 1, 'each', 0, 'pending')
                """
            )
        )
        material_id = connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()

    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO orders (
                    requested_by_user_id,
                    material_id,
                    requested_quantity,
                    status
                )
                VALUES (:user_id, :material_id, 1, 'unknown')
                """
            ),
            {"user_id": user_id, "material_id": material_id},
        )

    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO orders (
                    requested_by_user_id,
                    material_id,
                    requested_quantity,
                    status
                )
                VALUES (:user_id, 999999999, 1, 'submitted')
                """
            ),
            {"user_id": user_id},
        )


def test_migrations_can_downgrade_and_reapply() -> None:
    config = _script_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
    assert current_revision == ScriptDirectory.from_config(config).get_current_head()


def test_legacy_nonapproved_reservations_are_normalized_during_upgrade() -> None:
    config = _script_config()
    command.downgrade(config, "20260812_0002")
    try:
        with engine.begin() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            connection.execute(text("DELETE FROM orders"))
            connection.execute(text("DELETE FROM materials"))
            connection.execute(text("DELETE FROM users"))
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            connection.execute(text(
                "INSERT INTO users (username, email, password_hash, role) "
                "VALUES ('legacy_user', 'legacy@example.com', 'hash', 'viewer')"
            ))
            user_id = connection.execute(text("SELECT LAST_INSERT_ID()")) .scalar_one()
            connection.execute(text(
                "INSERT INTO materials (material_code, material_name, material_type, quantity_available, unit, minimum_quantity, qc_status) "
                "VALUES ('LEGACY-RESERVATION', 'Legacy', 'test', 5, 'each', 0, 'pending')"
            ))
            material_id = connection.execute(text("SELECT LAST_INSERT_ID()")) .scalar_one()
            connection.execute(
                text(
                    "INSERT INTO orders (requested_by_user_id, material_id, requested_quantity, reserved_quantity, status) "
                    "VALUES (:user_id, :material_id, 2, 2, 'submitted')"
                ),
                {"user_id": user_id, "material_id": material_id},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            reserved = connection.execute(
                text("SELECT reserved_quantity FROM orders WHERE material_id = :material_id"),
                {"material_id": material_id},
            ).scalar_one()
        assert reserved == 0
    finally:
        command.upgrade(config, "head")
