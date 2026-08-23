import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.pagination import Page, build_page, page_offset
from src.order.schemas import OrderArchive, OrderCreate, OrderRead, OrderReview
from src.user.schemas import UserRead
from src.utils.constant import PERMISSION_ORDER_READ_ALL, role_has_permission


ORDER_STATUS_SUBMITTED = "submitted"
ORDER_STATUS_APPROVED = "approved"
ORDER_STATUS_REJECTED = "rejected"
ORDER_STATUS_FULFILLED = "fulfilled"
ORDER_STATUS_CANCELED = "canceled"
ACTIVE_ORDER_STATUSES = (ORDER_STATUS_SUBMITTED, ORDER_STATUS_APPROVED)

AUDIT_ORDER_RESERVATION_CREATED = "order_reservation_created"
AUDIT_ORDER_FULFILLED = "order_fulfilled"
AUDIT_ORDER_RESERVATION_RELEASED = "order_reservation_released"
AUDIT_ORDER_ARCHIVED = "order_archived"


def _row_to_order(row) -> OrderRead | None:
    if row is None:
        return None
    return OrderRead(**row)


def _outcome_notes(payload: OrderReview | None) -> str | None:
    if payload is None:
        return None
    return payload.outcome_notes


def _inventory_audit_value(
    quantity_available: int,
    quantity_reserved: int,
) -> str:
    return json.dumps(
        {
            "quantity_available": quantity_available,
            "quantity_reserved": quantity_reserved,
        },
        separators=(",", ":"),
    )


def _order_audit_reason(
    order_id: int,
    action: str,
    payload: OrderReview | None,
) -> str:
    reason = f"Order #{order_id} {action}."
    notes = _outcome_notes(payload)
    return f"{reason} Outcome notes: {notes}" if notes else reason


def _log_order_inventory_audit(
    db: Session,
    *,
    user_id: int,
    material_id: int,
    operation_type: str,
    before_available: int,
    before_reserved: int,
    after_available: int,
    after_reserved: int,
    reason: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO inventory_audit_logs (
                user_id,
                material_id,
                operation_type,
                before_value,
                after_value,
                reason
            )
            VALUES (
                :user_id,
                :material_id,
                :operation_type,
                :before_value,
                :after_value,
                :reason
            )
            """
        ),
        {
            "user_id": user_id,
            "material_id": material_id,
            "operation_type": operation_type,
            "before_value": _inventory_audit_value(
                before_available,
                before_reserved,
            ),
            "after_value": _inventory_audit_value(
                after_available,
                after_reserved,
            ),
            "reason": reason,
        },
    )


def _can_access_order(order_row, current_user: UserRead) -> bool:
    return (
        role_has_permission(current_user.role, PERMISSION_ORDER_READ_ALL)
        or order_row["requested_by_user_id"] == current_user.id
    )


def _get_order_row(db: Session, order_id: int, *, for_update: bool = False):
    lock_clause = "FOR UPDATE" if for_update else ""
    return db.execute(
        text(
            f"""
            SELECT
                id,
                requested_by_user_id,
                (
                    SELECT username
                    FROM users
                    WHERE users.id = orders.requested_by_user_id
                ) AS requested_by_username,
                material_id,
                requested_quantity,
                reserved_quantity,
                status,
                request_notes,
                reviewed_by_user_id,
                reviewed_at,
                outcome_notes,
                is_archived,
                archived_at,
                archived_by_user_id,
                archive_reason,
                created_at,
                updated_at
            FROM orders
            WHERE id = :order_id
            {lock_clause}
            """
        ),
        {"order_id": order_id},
    ).mappings().first()


def _get_material_inventory(db: Session, material_id: int, *, for_update: bool = False):
    lock_clause = "FOR UPDATE" if for_update else ""
    return db.execute(
        text(
            f"""
            SELECT quantity_available, quantity_reserved, is_archived
            FROM materials
            WHERE id = :material_id
            {lock_clause}
            """
        ),
        {"material_id": material_id},
    ).mappings().first()


def create_order(
    db: Session,
    current_user: UserRead,
    payload: OrderCreate,
) -> tuple[OrderRead | None, str | None]:
    material = _get_material_inventory(db, payload.material_id, for_update=True)
    if material is None:
        return None, "material_not_found"
    if material["is_archived"]:
        return None, "archived_material"
    available_to_order = material["quantity_available"] - material["quantity_reserved"]
    if available_to_order < payload.requested_quantity:
        return None, "insufficient_quantity"

    db.execute(
        text(
            """
            INSERT INTO orders (
                requested_by_user_id,
                material_id,
                requested_quantity,
                request_notes
            )
            VALUES (
                :requested_by_user_id,
                :material_id,
                :requested_quantity,
                :request_notes
            )
            """
        ),
        {
            "requested_by_user_id": current_user.id,
            "material_id": payload.material_id,
            "requested_quantity": payload.requested_quantity,
            "request_notes": payload.request_notes,
        },
    )
    order_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()

    return get_order(db, order_id, current_user), None


def list_orders(
    db: Session,
    current_user: UserRead,
    status: str | None = None,
    material_id: int | None = None,
    requested_by_user_id: int | None = None,
    reviewed_by_user_id: int | None = None,
    include_archived: bool = False,
    active_only: bool = False,
    page: int = 1,
    size: int = 25,
) -> Page[OrderRead]:
    query = """
        SELECT
            orders.id,
            orders.requested_by_user_id,
            users.username AS requested_by_username,
            orders.material_id,
            orders.requested_quantity,
            orders.reserved_quantity,
            orders.status,
            orders.request_notes,
            orders.reviewed_by_user_id,
            orders.reviewed_at,
            orders.outcome_notes,
            orders.is_archived,
            orders.archived_at,
            orders.archived_by_user_id,
            orders.archive_reason,
            orders.created_at,
            orders.updated_at
        FROM orders
        JOIN users ON users.id = orders.requested_by_user_id
    """
    conditions = []
    params = {}

    if not role_has_permission(current_user.role, PERMISSION_ORDER_READ_ALL):
        conditions.append("requested_by_user_id = :current_user_id")
        params["current_user_id"] = current_user.id
    elif requested_by_user_id is not None:
        conditions.append("requested_by_user_id = :requested_by_user_id")
        params["requested_by_user_id"] = requested_by_user_id

    if not include_archived:
        conditions.append("is_archived = FALSE")

    if active_only:
        active_status_params = {
            f"active_status_{index}": active_status
            for index, active_status in enumerate(ACTIVE_ORDER_STATUSES)
        }
        conditions.append(
            "status IN (" + ", ".join(f":{name}" for name in active_status_params) + ")"
        )
        params.update(active_status_params)

    if status is not None:
        conditions.append("status = :status")
        params["status"] = status

    if material_id is not None:
        conditions.append("material_id = :material_id")
        params["material_id"] = material_id

    if reviewed_by_user_id is not None:
        conditions.append("reviewed_by_user_id = :reviewed_by_user_id")
        params["reviewed_by_user_id"] = reviewed_by_user_id

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query += where_clause

    total = db.execute(
        text(f"SELECT COUNT(*) FROM orders{where_clause}"),
        params,
    ).scalar_one()
    query += " ORDER BY id DESC LIMIT :size OFFSET :offset"
    rows = db.execute(
        text(query),
        {**params, "size": size, "offset": page_offset(page, size)},
    ).mappings().all()
    return build_page(
        [OrderRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )


def get_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
) -> OrderRead | None:
    row = _get_order_row(db, order_id)
    if row is None or not _can_access_order(row, current_user):
        return None
    return OrderRead(**row)


def approve_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id, for_update=True)
    if order is None:
        return None, "not_found"
    if order["status"] != ORDER_STATUS_SUBMITTED:
        return None, "invalid_status"

    material = _get_material_inventory(db, order["material_id"], for_update=True)
    if material is None:
        return None, "material_not_found"
    if material["is_archived"]:
        return None, "archived_material"

    available_to_reserve = material["quantity_available"] - material["quantity_reserved"]
    if available_to_reserve < order["requested_quantity"]:
        return None, "insufficient_quantity"

    db.execute(
        text(
            """
            UPDATE materials
            SET quantity_reserved = quantity_reserved + :requested_quantity
            WHERE id = :material_id
            """
        ),
        {
            "material_id": order["material_id"],
            "requested_quantity": order["requested_quantity"],
        },
    )
    db.execute(
        text(
            """
            UPDATE orders
            SET
                status = :status,
                reserved_quantity = :reserved_quantity,
                reviewed_by_user_id = :reviewed_by_user_id,
                reviewed_at = CURRENT_TIMESTAMP,
                outcome_notes = :outcome_notes
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "status": ORDER_STATUS_APPROVED,
            "reserved_quantity": order["requested_quantity"],
            "reviewed_by_user_id": current_user.id,
            "outcome_notes": _outcome_notes(payload),
        },
    )
    _log_order_inventory_audit(
        db,
        user_id=current_user.id,
        material_id=order["material_id"],
        operation_type=AUDIT_ORDER_RESERVATION_CREATED,
        before_available=material["quantity_available"],
        before_reserved=material["quantity_reserved"],
        after_available=material["quantity_available"],
        after_reserved=material["quantity_reserved"] + order["requested_quantity"],
        reason=_order_audit_reason(order_id, "approved; reservation created", payload),
    )
    updated_order = _row_to_order(_get_order_row(db, order_id))
    db.commit()

    return updated_order, None


def reject_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id, for_update=True)
    if order is None:
        return None, "not_found"
    if order["status"] != ORDER_STATUS_SUBMITTED:
        return None, "invalid_status"

    db.execute(
        text(
            """
            UPDATE orders
            SET
                status = :status,
                reserved_quantity = 0,
                reviewed_by_user_id = :reviewed_by_user_id,
                reviewed_at = CURRENT_TIMESTAMP,
                outcome_notes = :outcome_notes
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "status": ORDER_STATUS_REJECTED,
            "reviewed_by_user_id": current_user.id,
            "outcome_notes": _outcome_notes(payload),
        },
    )
    updated_order = _row_to_order(_get_order_row(db, order_id))
    db.commit()

    return updated_order, None


def fulfill_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id, for_update=True)
    if order is None:
        return None, "not_found"
    if order["status"] != ORDER_STATUS_APPROVED:
        return None, "invalid_status"

    material = _get_material_inventory(db, order["material_id"], for_update=True)
    if material is None:
        return None, "material_not_found"
    if material["is_archived"]:
        return None, "archived_material"

    if (
        material["quantity_available"] < order["reserved_quantity"]
        or material["quantity_reserved"] < order["reserved_quantity"]
    ):
        return None, "insufficient_quantity"

    db.execute(
        text(
            """
            UPDATE materials
            SET
                quantity_available = quantity_available - :reserved_quantity,
                quantity_reserved = quantity_reserved - :reserved_quantity
            WHERE id = :material_id
            """
        ),
        {
            "material_id": order["material_id"],
            "reserved_quantity": order["reserved_quantity"],
        },
    )
    db.execute(
        text(
            """
            UPDATE orders
            SET
                status = :status,
                reserved_quantity = 0,
                reviewed_by_user_id = :reviewed_by_user_id,
                reviewed_at = CURRENT_TIMESTAMP,
                outcome_notes = :outcome_notes
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "status": ORDER_STATUS_FULFILLED,
            "reviewed_by_user_id": current_user.id,
            "outcome_notes": _outcome_notes(payload),
        },
    )
    _log_order_inventory_audit(
        db,
        user_id=current_user.id,
        material_id=order["material_id"],
        operation_type=AUDIT_ORDER_FULFILLED,
        before_available=material["quantity_available"],
        before_reserved=material["quantity_reserved"],
        after_available=material["quantity_available"] - order["reserved_quantity"],
        after_reserved=material["quantity_reserved"] - order["reserved_quantity"],
        reason=_order_audit_reason(order_id, "fulfilled", payload),
    )
    updated_order = _row_to_order(_get_order_row(db, order_id))
    db.commit()

    return updated_order, None


def cancel_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id, for_update=True)
    if order is None or not _can_access_order(order, current_user):
        return None, "not_found"
    if order["status"] not in {ORDER_STATUS_SUBMITTED, ORDER_STATUS_APPROVED}:
        return None, "invalid_status"

    if order["status"] == ORDER_STATUS_APPROVED and order["reserved_quantity"] > 0:
        material = _get_material_inventory(db, order["material_id"], for_update=True)
        if material is None:
            return None, "material_not_found"
        if material["quantity_reserved"] < order["reserved_quantity"]:
            return None, "insufficient_quantity"

        db.execute(
            text(
                """
                UPDATE materials
                SET quantity_reserved = quantity_reserved - :reserved_quantity
                WHERE id = :material_id
                """
            ),
            {
                "material_id": order["material_id"],
                "reserved_quantity": order["reserved_quantity"],
            },
        )
        _log_order_inventory_audit(
            db,
            user_id=current_user.id,
            material_id=order["material_id"],
            operation_type=AUDIT_ORDER_RESERVATION_RELEASED,
            before_available=material["quantity_available"],
            before_reserved=material["quantity_reserved"],
            after_available=material["quantity_available"],
            after_reserved=material["quantity_reserved"] - order["reserved_quantity"],
            reason=_order_audit_reason(
                order_id,
                "canceled; reservation released",
                payload,
            ),
        )

    db.execute(
        text(
            """
            UPDATE orders
            SET
                status = :status,
                reserved_quantity = 0,
                reviewed_by_user_id = :reviewed_by_user_id,
                reviewed_at = CURRENT_TIMESTAMP,
                outcome_notes = :outcome_notes
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "status": ORDER_STATUS_CANCELED,
            "reviewed_by_user_id": current_user.id,
            "outcome_notes": _outcome_notes(payload),
        },
    )
    updated_order = _row_to_order(_get_order_row(db, order_id))
    db.commit()

    return updated_order, None


def archive_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderArchive,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id, for_update=True)
    if order is None or not _can_access_order(order, current_user):
        return None, "not_found"
    if order["is_archived"]:
        return None, "already_archived"
    if order["status"] in {ORDER_STATUS_SUBMITTED, ORDER_STATUS_APPROVED}:
        return None, "invalid_status"

    material = _get_material_inventory(db, order["material_id"], for_update=True)
    if material is None:
        return None, "material_not_found"

    db.execute(
        text(
            """
            UPDATE orders
            SET
                is_archived = TRUE,
                archived_at = CURRENT_TIMESTAMP,
                archived_by_user_id = :archived_by_user_id,
                archive_reason = :archive_reason
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "archived_by_user_id": current_user.id,
            "archive_reason": payload.reason,
        },
    )
    _log_order_inventory_audit(
        db,
        user_id=current_user.id,
        material_id=order["material_id"],
        operation_type=AUDIT_ORDER_ARCHIVED,
        before_available=material["quantity_available"],
        before_reserved=material["quantity_reserved"],
        after_available=material["quantity_available"],
        after_reserved=material["quantity_reserved"],
        reason=f"Order #{order_id} archived. Reason: {payload.reason}",
    )
    updated_order = _row_to_order(_get_order_row(db, order_id))
    db.commit()

    return updated_order, None
