"""Create the initial application schema.

Revision ID: 20260812_0001
Revises:
Create Date: 2026-08-12

The table guards let an existing, unversioned installation adopt Alembic. A
fresh database is still built solely from this migration.
"""

from collections.abc import Callable
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260812_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_if_missing(table_name: str, create_table: Callable[[], None]) -> None:
    if not sa.inspect(op.get_bind()).has_table(table_name):
        create_table()


def upgrade() -> None:
    _create_if_missing(
        "test_table",
        lambda: op.create_table(
            "test_table",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_test_table"),
        ),
    )
    _create_if_missing(
        "users",
        lambda: op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'viewer'"),
            ),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_users"),
            sa.UniqueConstraint("username", name="uq_users_username"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        ),
    )
    _create_if_missing(
        "token_table",
        lambda: op.create_table(
            "token_table",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name="fk_token_table_user_id_users"
            ),
            sa.PrimaryKeyConstraint("id", name="pk_token_table"),
            sa.UniqueConstraint("token", name="uq_token_table_token"),
        ),
    )
    _create_if_missing(
        "locations",
        lambda: op.create_table(
            "locations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("location_type", sa.String(length=80), nullable=False),
            sa.Column("parent_location_id", sa.Integer(), nullable=True),
            sa.Column("temperature_zone", sa.String(length=80), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                mysql.TIMESTAMP(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_locations"),
        ),
    )
    _create_if_missing(
        "materials",
        lambda: op.create_table(
            "materials",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("material_code", sa.String(length=80), nullable=False),
            sa.Column("material_name", sa.String(length=255), nullable=False),
            sa.Column("material_type", sa.String(length=80), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=255), nullable=True),
            sa.Column("quantity_available", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("unit", sa.String(length=40), nullable=False),
            sa.Column("minimum_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("availability_status", sa.String(length=40), nullable=False, server_default=sa.text("'available'")),
            sa.Column("qc_status", sa.String(length=40), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("storage_condition", sa.String(length=120), nullable=True),
            sa.Column("location_id", sa.Integer(), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("archived_at", mysql.TIMESTAMP(), nullable=True),
            sa.Column("archived_by_user_id", sa.Integer(), nullable=True),
            sa.Column("archive_reason", sa.Text(), nullable=True),
            sa.Column("created_at", mysql.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", mysql.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="pk_materials"),
            sa.UniqueConstraint("material_code", name="uq_materials_material_code"),
        ),
    )
    _create_if_missing(
        "inventory_audit_logs",
        lambda: op.create_table(
            "inventory_audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("material_id", sa.Integer(), nullable=False),
            sa.Column("operation_type", sa.String(length=80), nullable=False),
            sa.Column("before_value", sa.String(length=255), nullable=False),
            sa.Column("after_value", sa.String(length=255), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("created_at", mysql.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_user_id_users"),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], name="fk_audit_material_id_materials"),
            sa.PrimaryKeyConstraint("id", name="pk_inventory_audit_logs"),
        ),
    )
    _create_if_missing(
        "orders",
        lambda: op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
            sa.Column("material_id", sa.Integer(), nullable=False),
            sa.Column("requested_quantity", sa.Integer(), nullable=False),
            sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("status", sa.String(length=40), nullable=False, server_default=sa.text("'submitted'")),
            sa.Column("request_notes", sa.Text(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", mysql.TIMESTAMP(), nullable=True),
            sa.Column("outcome_notes", sa.Text(), nullable=True),
            sa.Column("created_at", mysql.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", mysql.TIMESTAMP(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], name="fk_orders_requested_by_user_id_users"),
            sa.ForeignKeyConstraint(["material_id"], ["materials.id"], name="fk_orders_material_id_materials"),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], name="fk_orders_reviewed_by_user_id_users"),
            sa.PrimaryKeyConstraint("id", name="pk_orders"),
        ),
    )


def downgrade() -> None:
    for table_name in (
        "orders",
        "inventory_audit_logs",
        "materials",
        "locations",
        "token_table",
        "users",
        "test_table",
    ):
        if sa.inspect(op.get_bind()).has_table(table_name):
            op.drop_table(table_name)
