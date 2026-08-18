"""Add domain constraints, relationship policies, and query indexes.
Revision ID: 20260812_0003
Revises: 20260812_0002
Create Date: 2026-08-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260812_0003"
down_revision: Union[str, Sequence[str], None] = "20260812_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DOMAIN_CHECKS = (
    (
        "ck_users_role",
        "users",
        "role IN ('viewer', 'staff', 'admin')",
    ),
    (
        "ck_materials_qc_status",
        "materials",
        "qc_status IN ('pending', 'passed', 'failed')",
    ),
    (
        "ck_materials_reserved_within_available",
        "materials",
        "quantity_reserved <= quantity_available",
    ),
    (
        "ck_orders_status",
        "orders",
        "status IN ('submitted', 'approved', 'rejected', 'fulfilled', 'canceled')",
    ),
    (
        "ck_orders_reserved_within_requested",
        "orders",
        "reserved_quantity <= requested_quantity",
    ),
    (
        "ck_orders_reservation_matches_status",
        "orders",
        "(status = 'approved' AND reserved_quantity = requested_quantity) "
        "OR (status <> 'approved' AND reserved_quantity = 0)",
    ),
)

QUERY_INDEXES = (
    ("ix_materials_source", "materials", ["source"]),
    ("ix_orders_status", "orders", ["status"]),
    (
        "ix_orders_requester_archived_status_id",
        "orders",
        ["requested_by_user_id", "is_archived", "status", "id"],
    ),
    (
        "ix_orders_material_status",
        "orders",
        ["material_id", "status"],
    ),
    (
        "ix_orders_reviewer_status",
        "orders",
        ["reviewed_by_user_id", "status"],
    ),
    (
        "ix_inventory_audit_logs_material_created_at",
        "inventory_audit_logs",
        ["material_id", "created_at", "id"],
    ),
    (
        "ix_inventory_audit_logs_user_created_at",
        "inventory_audit_logs",
        ["user_id", "created_at", "id"],
    ),
    (
        "ix_inventory_audit_logs_operation_created_at",
        "inventory_audit_logs",
        ["operation_type", "created_at", "id"],
    ),
)

RELATIONSHIPS = (
    (
        "fk_token_table_user_id_users",
        "token_table",
        "users",
        ["user_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_locations_parent_location_id_locations",
        "locations",
        "locations",
        ["parent_location_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_materials_location_id_locations",
        "materials",
        "locations",
        ["location_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_materials_archived_by_user_id_users",
        "materials",
        "users",
        ["archived_by_user_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_orders_archived_by_user_id_users",
        "orders",
        "users",
        ["archived_by_user_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_audit_user_id_users",
        "inventory_audit_logs",
        "users",
        ["user_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_audit_material_id_materials",
        "inventory_audit_logs",
        "materials",
        ["material_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_orders_requested_by_user_id_users",
        "orders",
        "users",
        ["requested_by_user_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_orders_material_id_materials",
        "orders",
        "materials",
        ["material_id"],
        ["id"],
        "RESTRICT",
    ),
    (
        "fk_orders_reviewed_by_user_id_users",
        "orders",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        "RESTRICT",
    ),
)


def _check_names(table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(table_name)
        if constraint.get("name")
    }

def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }

def _foreign_keys(table_name: str) -> list[dict]:
    return sa.inspect(op.get_bind()).get_foreign_keys(table_name)

def _relationship_matches(
    constraint: dict,
    referent_table: str,
    local_columns: list[str],
    remote_columns: list[str],
) -> bool:
    return (
        constraint["referred_table"] == referent_table
        and constraint["constrained_columns"] == local_columns
        and constraint["referred_columns"] == remote_columns
    )

def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET reserved_quantity = 0
            WHERE status <> 'approved' AND reserved_quantity <> 0
            """
        )
    )

    invalid_data_checks = {
        "users.role": "SELECT COUNT(*) FROM users WHERE role NOT IN ('viewer', 'staff', 'admin')",
        "materials.qc_status": "SELECT COUNT(*) FROM materials WHERE qc_status NOT IN ('pending', 'passed', 'failed')",
        "materials.quantities": "SELECT COUNT(*) FROM materials WHERE quantity_available < 0 OR quantity_reserved < 0 OR minimum_quantity < 0 OR quantity_reserved > quantity_available",
        "orders.status_or_quantities": "SELECT COUNT(*) FROM orders WHERE status NOT IN ('submitted', 'approved', 'rejected', 'fulfilled', 'canceled') OR requested_quantity <= 0 OR reserved_quantity < 0 OR reserved_quantity > requested_quantity OR (status = 'approved' AND reserved_quantity <> requested_quantity) OR (status <> 'approved' AND reserved_quantity <> 0)",
    }
    invalid_fields = [
        label
        for label, query in invalid_data_checks.items()
        if op.get_bind().execute(sa.text(query)).scalar_one() > 0
    ]
    if invalid_fields:
        raise RuntimeError(
            "Migration blocked by invalid legacy data in: "
            + ", ".join(invalid_fields)
            + ". Correct these rows and rerun `alembic upgrade head`."
        )

    for name, table_name, condition in DOMAIN_CHECKS:
        if name not in _check_names(table_name):
            op.create_check_constraint(name, table_name, condition)

    for name, table_name, columns in QUERY_INDEXES:
        if name not in _index_names(table_name):
            op.create_index(name, table_name, columns, unique=False)

    for (
        name,
        source_table,
        referent_table,
        local_columns,
        remote_columns,
        ondelete,
    ) in RELATIONSHIPS:
        matching = [
            constraint
            for constraint in _foreign_keys(source_table)
            if _relationship_matches(
                constraint,
                referent_table,
                local_columns,
                remote_columns,
            )
        ]
        if matching and matching[0].get("options", {}).get("ondelete") == ondelete:
            continue
        for constraint in matching:
            op.drop_constraint(constraint["name"], source_table, type_="foreignkey")
        op.create_foreign_key(
            name,
            source_table,
            referent_table,
            local_columns,
            remote_columns,
            ondelete=ondelete,
        )

def downgrade() -> None:
    for name, source_table, referent_table, local_columns, remote_columns, _ in reversed(RELATIONSHIPS):
        matching = [
            constraint
            for constraint in _foreign_keys(source_table)
            if _relationship_matches(
                constraint,
                referent_table,
                local_columns,
                remote_columns,
            )
        ]
        for constraint in matching:
            op.drop_constraint(constraint["name"], source_table, type_="foreignkey")

    for name, table_name, _ in reversed(QUERY_INDEXES):
        if name in _index_names(table_name):
            op.drop_index(name, table_name=table_name)

    for name, source_table, referent_table, local_columns, remote_columns, _ in RELATIONSHIPS:
        op.create_foreign_key(
            name,
            source_table,
            referent_table,
            local_columns,
            remote_columns,
        )

    for name, table_name, _ in reversed(DOMAIN_CHECKS):
        if name in _check_names(table_name):
            op.drop_constraint(name, table_name, type_="check")
