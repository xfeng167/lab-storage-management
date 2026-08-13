"""Add persistent login throttling and token-expiry support.

Revision ID: 20260812_0004
Revises: 20260812_0003
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260812_0004"
down_revision: Union[str, Sequence[str], None] = "20260812_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("application_locks"):
        op.create_table(
            "application_locks",
            sa.Column("lock_name", sa.String(length=80), nullable=False),
            sa.PrimaryKeyConstraint("lock_name", name="pk_application_locks"),
        )
        op.execute(
            sa.text(
                "INSERT INTO application_locks (lock_name) VALUES ('location_hierarchy')"
            )
        )
    if not inspector.has_table("login_throttle"):
        op.create_table(
            "login_throttle",
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), nullable=False),
            sa.Column("window_started_at", mysql.TIMESTAMP(), nullable=False),
            sa.Column("locked_until", mysql.TIMESTAMP(), nullable=True),
            sa.Column(
                "updated_at",
                mysql.TIMESTAMP(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.CheckConstraint("failed_attempts >= 0", name="ck_login_throttle_nonnegative_attempts"),
            sa.PrimaryKeyConstraint("username", name="pk_login_throttle"),
        )

    token_indexes = {index["name"] for index in inspector.get_indexes("token_table")}
    if "ix_token_table_created_at" not in token_indexes:
        op.create_index("ix_token_table_created_at", "token_table", ["created_at"])

    for column_name in ("before_value", "after_value"):
        column = next(
            column
            for column in inspector.get_columns("inventory_audit_logs")
            if column["name"] == column_name
        )
        if not isinstance(column["type"], mysql.TEXT):
            op.alter_column(
                "inventory_audit_logs",
                column_name,
                existing_type=sa.String(length=255),
                type_=sa.Text(),
                existing_nullable=False,
            )


def downgrade() -> None:
    op.alter_column(
        "inventory_audit_logs",
        "after_value",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "inventory_audit_logs",
        "before_value",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_index("ix_token_table_created_at", table_name="token_table")
    op.drop_table("login_throttle")
    op.drop_table("application_locks")
