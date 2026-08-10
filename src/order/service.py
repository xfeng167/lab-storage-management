from sqlalchemy import text
from sqlalchemy.orm import Session

from src.order.schemas import OrderCreate, OrderRead, OrderReview
from src.user.schemas import UserRead
from src.utils.constant import ROLE_ADMIN


ORDER_STATUS_SUBMITTED = "submitted"
ORDER_STATUS_APPROVED = "approved"
ORDER_STATUS_REJECTED = "rejected"
ORDER_STATUS_FULFILLED = "fulfilled"
ORDER_STATUS_CANCELED = "canceled"


def _row_to_order(row) -> OrderRead | None:
    if row is None:
        return None
    return OrderRead(**row)


def _outcome_notes(payload: OrderReview | None) -> str | None:
    if payload is None:
        return None
    return payload.outcome_notes


def _can_access_order(order_row, current_user: UserRead) -> bool:
    return (
        current_user.role == ROLE_ADMIN
        or order_row["requested_by_user_id"] == current_user.id
    )


def _get_order_row(db: Session, order_id: int):
    return db.execute(
        text(
            """
            SELECT
                id,
                requested_by_user_id,
                material_id,
                requested_quantity,
                reserved_quantity,
                status,
                request_notes,
                reviewed_by_user_id,
                reviewed_at,
                outcome_notes,
                created_at,
                updated_at
            FROM orders
            WHERE id = :order_id
            """
        ),
        {"order_id": order_id},
    ).mappings().first()


def _get_material_inventory(db: Session, material_id: int):
    return db.execute(
        text(
            """
            SELECT quantity_available, quantity_reserved, is_archived
            FROM materials
            WHERE id = :material_id
            """
        ),
        {"material_id": material_id},
    ).mappings().first()


def create_order(
    db: Session,
    current_user: UserRead,
    payload: OrderCreate,
) -> tuple[OrderRead | None, str | None]:
    material = _get_material_inventory(db, payload.material_id)
    if material is None:
        return None, "material_not_found"
    if material["is_archived"]:
        return None, "archived_material"

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
) -> list[OrderRead]:
    query = """
        SELECT
            id,
            requested_by_user_id,
            material_id,
            requested_quantity,
            reserved_quantity,
            status,
            request_notes,
            reviewed_by_user_id,
            reviewed_at,
            outcome_notes,
            created_at,
            updated_at
        FROM orders
    """
    conditions = []
    params = {}

    if current_user.role != ROLE_ADMIN:
        conditions.append("requested_by_user_id = :current_user_id")
        params["current_user_id"] = current_user.id
    elif requested_by_user_id is not None:
        conditions.append("requested_by_user_id = :requested_by_user_id")
        params["requested_by_user_id"] = requested_by_user_id

    if status is not None:
        conditions.append("status = :status")
        params["status"] = status

    if material_id is not None:
        conditions.append("material_id = :material_id")
        params["material_id"] = material_id

    if reviewed_by_user_id is not None:
        conditions.append("reviewed_by_user_id = :reviewed_by_user_id")
        params["reviewed_by_user_id"] = reviewed_by_user_id

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"
    rows = db.execute(text(query), params).mappings().all()
    return [OrderRead(**row) for row in rows]


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
    order = _get_order_row(db, order_id)
    if order is None:
        return None, "not_found"
    if order["status"] != ORDER_STATUS_SUBMITTED:
        return None, "invalid_status"

    material = _get_material_inventory(db, order["material_id"])
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
    db.commit()

    return _row_to_order(_get_order_row(db, order_id)), None


def reject_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id)
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
    db.commit()

    return _row_to_order(_get_order_row(db, order_id)), None


def fulfill_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id)
    if order is None:
        return None, "not_found"
    if order["status"] != ORDER_STATUS_APPROVED:
        return None, "invalid_status"

    material = _get_material_inventory(db, order["material_id"])
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
    db.commit()

    return _row_to_order(_get_order_row(db, order_id)), None


def cancel_order(
    db: Session,
    order_id: int,
    current_user: UserRead,
    payload: OrderReview | None = None,
) -> tuple[OrderRead | None, str | None]:
    order = _get_order_row(db, order_id)
    if order is None or not _can_access_order(order, current_user):
        return None, "not_found"
    if order["status"] not in {ORDER_STATUS_SUBMITTED, ORDER_STATUS_APPROVED}:
        return None, "invalid_status"

    if order["status"] == ORDER_STATUS_APPROVED and order["reserved_quantity"] > 0:
        material = _get_material_inventory(db, order["material_id"])
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

    db.execute(
        text(
            """
            UPDATE orders
            SET
                status = :status,
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
    db.commit()

    return _row_to_order(_get_order_row(db, order_id)), None
