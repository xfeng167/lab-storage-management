"""Bring legacy installations to the current constrained schema.

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260812_0002"
down_revision: Union[str, Sequence[str], None] = "20260812_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _add_column_if_missing(
    table_name: str,
    column_name: str,
    column: sa.Column,
) -> None:
    if column_name not in _column_names(table_name):
        op.add_column(table_name, column)


def _drop_column_if_present(table_name: str, column_name: str) -> None:
    if column_name in _column_names(table_name):
        op.drop_column(table_name, column_name)


def _index_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(index["column_names"])
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _create_index_if_missing(
    name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if tuple(columns) not in _index_column_sets(table_name):
        op.create_index(name, table_name, columns, unique=False)


def _foreign_key_pairs(table_name: str) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    return {
        (
            tuple(constraint["constrained_columns"]),
            constraint["referred_table"],
            tuple(constraint["referred_columns"]),
        )
        for constraint in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    }


def _create_foreign_key_if_missing(
    name: str,
    source_table: str,
    referent_table: str,
    local_columns: list[str],
    remote_columns: list[str],
) -> None:
    key = (tuple(local_columns), referent_table, tuple(remote_columns))
    if key not in _foreign_key_pairs(source_table):
        op.create_foreign_key(
            name,
            source_table,
            referent_table,
            local_columns,
            remote_columns,
        )


def _check_names(table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(table_name)
        if constraint.get("name")
    }


def _create_check_if_missing(name: str, table_name: str, condition: str) -> None:
    if name not in _check_names(table_name):
        op.create_check_constraint(name, table_name, condition)


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("test_table"):
        op.drop_table("test_table")

    _add_column_if_missing(
        "users",
        "profile_picture",
        sa.Column("profile_picture", mysql.MEDIUMTEXT(), nullable=True),
    )
    _add_column_if_missing(
        "orders",
        "is_archived",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    _add_column_if_missing(
        "orders",
        "archived_at",
        sa.Column("archived_at", mysql.TIMESTAMP(), nullable=True),
    )
    _add_column_if_missing(
        "orders",
        "archived_by_user_id",
        sa.Column("archived_by_user_id", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        "orders",
        "archive_reason",
        sa.Column("archive_reason", sa.Text(), nullable=True),
    )
    _drop_column_if_present("materials", "availability_status")

    _create_index_if_missing("ix_locations_parent_location_id", "locations", ["parent_location_id"])
    _create_index_if_missing("ix_materials_location_id", "materials", ["location_id"])
    _create_index_if_missing("ix_materials_archived_by_user_id", "materials", ["archived_by_user_id"])
    _create_index_if_missing("ix_materials_active_search", "materials", ["is_archived", "material_type", "qc_status"])
    _create_index_if_missing("ix_orders_archived_by_user_id", "orders", ["archived_by_user_id"])
    _create_index_if_missing("ix_orders_status_archived", "orders", ["status", "is_archived"])
    _create_index_if_missing("ix_inventory_audit_logs_created_at", "inventory_audit_logs", ["created_at"])

    _create_foreign_key_if_missing(
        "fk_locations_parent_location_id_locations",
        "locations",
        "locations",
        ["parent_location_id"],
        ["id"],
    )
    _create_foreign_key_if_missing(
        "fk_materials_location_id_locations",
        "materials",
        "locations",
        ["location_id"],
        ["id"],
    )
    _create_foreign_key_if_missing(
        "fk_materials_archived_by_user_id_users",
        "materials",
        "users",
        ["archived_by_user_id"],
        ["id"],
    )
    _create_foreign_key_if_missing(
        "fk_orders_archived_by_user_id_users",
        "orders",
        "users",
        ["archived_by_user_id"],
        ["id"],
    )

    _create_check_if_missing(
        "ck_materials_nonnegative_quantities",
        "materials",
        "quantity_available >= 0 AND quantity_reserved >= 0 AND minimum_quantity >= 0",
    )
    _create_check_if_missing(
        "ck_orders_positive_requested_quantity",
        "orders",
        "requested_quantity > 0",
    )
    _create_check_if_missing(
        "ck_orders_nonnegative_reserved_quantity",
        "orders",
        "reserved_quantity >= 0",
    )


def downgrade() -> None:
    for name, table_name in (
        ("ck_orders_nonnegative_reserved_quantity", "orders"),
        ("ck_orders_positive_requested_quantity", "orders"),
        ("ck_materials_nonnegative_quantities", "materials"),
    ):
        if name in _check_names(table_name):
            op.drop_constraint(name, table_name, type_="check")

    for name, table_name in (
        ("fk_orders_archived_by_user_id_users", "orders"),
        ("fk_materials_archived_by_user_id_users", "materials"),
        ("fk_materials_location_id_locations", "materials"),
        ("fk_locations_parent_location_id_locations", "locations"),
    ):
        foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        if any(constraint.get("name") == name for constraint in foreign_keys):
            op.drop_constraint(name, table_name, type_="foreignkey")

    for name, table_name in (
        ("ix_inventory_audit_logs_created_at", "inventory_audit_logs"),
        ("ix_orders_status_archived", "orders"),
        ("ix_orders_archived_by_user_id", "orders"),
        ("ix_materials_active_search", "materials"),
        ("ix_materials_archived_by_user_id", "materials"),
        ("ix_materials_location_id", "materials"),
        ("ix_locations_parent_location_id", "locations"),
    ):
        if any(index.get("name") == name for index in sa.inspect(op.get_bind()).get_indexes(table_name)):
            op.drop_index(name, table_name=table_name)

    op.add_column(
        "materials",
        sa.Column("availability_status", sa.String(length=40), nullable=False, server_default=sa.text("'available'")),
    )
    op.execute(
        sa.text(
            """
            UPDATE materials
            SET availability_status = CASE
                WHEN quantity_available - quantity_reserved <= 0 THEN 'unavailable'
                WHEN quantity_available - quantity_reserved <= minimum_quantity THEN 'low_stock'
                ELSE 'available'
            END
            """
        )
    )
    for column_name in ("archive_reason", "archived_by_user_id", "archived_at", "is_archived"):
        if column_name in _column_names("orders"):
            op.drop_column("orders", column_name)
    if "profile_picture" in _column_names("users"):
        op.drop_column("users", "profile_picture")
    if not sa.inspect(op.get_bind()).has_table("test_table"):
        op.create_table(
            "test_table",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_test_table"),
        )
