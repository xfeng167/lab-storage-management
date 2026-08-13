from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.auth.dependencies import (
    require_order_archiver,
    require_order_canceler,
    require_order_creator,
    require_order_reader,
    require_order_reviewer,
)
from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from src.core.errors import bad_request, conflict, not_found
from src.db.connection import get_db
from src.order import service
from src.order.schemas import OrderArchive, OrderCreate, OrderRead, OrderReview, OrderStatus
from src.user.schemas import UserRead

router = APIRouter()


def _raise_order_error(error: str | None, *, operation: str | None = None) -> None:
    if error in {"not_found", "material_not_found"}:
        code = "MATERIAL_NOT_FOUND" if error == "material_not_found" else "ORDER_NOT_FOUND"
        message = "Material not found" if error == "material_not_found" else "Order not found"
        raise not_found(code, message)
    if error == "invalid_status":
        raise conflict("ORDER_STATUS_CONFLICT", "Order status does not allow this operation")
    if error == "already_archived":
        raise conflict("ORDER_ALREADY_ARCHIVED", "Order is already archived")
    if error == "archived_material":
        raise conflict("MATERIAL_ARCHIVED", "Archived material cannot be ordered")
    if error == "insufficient_quantity":
        detail = {
            "create": "Insufficient unreserved stock to submit order",
            "approve": "Insufficient unreserved stock to approve order",
            "fulfill": "Reserved stock is inconsistent; order cannot be fulfilled",
            "cancel": "Reserved stock is inconsistent; order cannot be canceled",
        }.get(operation, "Insufficient quantity available")
        code = {
            "create": "ORDER_STOCK_INSUFFICIENT",
            "approve": "ORDER_STOCK_INSUFFICIENT",
            "fulfill": "ORDER_RESERVATION_INCONSISTENT",
            "cancel": "ORDER_RESERVATION_INCONSISTENT",
        }.get(operation, "INVENTORY_INSUFFICIENT")
        raise conflict(code, detail)
    raise bad_request("ORDER_OPERATION_FAILED", "Order operation failed")


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    description=(
        "Submit an order for an active material. Submission validates the material "
        "and requires enough unreserved stock for the requested quantity. Stock is "
        "validated again and reserved during approval."
    ),
)
def create_order(
    payload: OrderCreate,
    current_user: UserRead = Depends(require_order_creator),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.create_order(db, current_user, payload)
    if order is None:
        _raise_order_error(error, operation="create")
    return order


@router.get("", response_model=Page[OrderRead])
def list_orders(
    status: OrderStatus | None = None,
    material_id: int | None = None,
    requested_by_user_id: int | None = None,
    reviewed_by_user_id: int | None = None,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_order_reader),
    db: Session = Depends(get_db),
) -> Page[OrderRead]:
    return service.list_orders(
        db,
        current_user,
        status=status,
        material_id=material_id,
        requested_by_user_id=requested_by_user_id,
        reviewed_by_user_id=reviewed_by_user_id,
        include_archived=include_archived,
        page=page,
        size=size,
    )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    current_user: UserRead = Depends(require_order_reader),
    db: Session = Depends(get_db),
) -> OrderRead:
    order = service.get_order(db, order_id, current_user)
    if order is None:
        raise not_found("ORDER_NOT_FOUND", "Order not found")
    return order


@router.post(
    "/{order_id}/approve",
    response_model=OrderRead,
    description=(
        "Validate unreserved stock while locking the order and material rows. "
        "Approval succeeds only when quantity_available - quantity_reserved covers "
        "the requested quantity, which is then reserved in the same transaction."
    ),
)
def approve_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_order_reviewer),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.approve_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error, operation="approve")
    return order


@router.post("/{order_id}/reject", response_model=OrderRead)
def reject_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_order_reviewer),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.reject_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order


@router.post(
    "/{order_id}/fulfill",
    response_model=OrderRead,
    description=(
        "Revalidate that the approved reservation is still backed by both available "
        "and reserved inventory, then deduct it in the same transaction."
    ),
)
def fulfill_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_order_reviewer),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.fulfill_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error, operation="fulfill")
    return order


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    description=(
        "Cancel a submitted order without touching inventory, or validate and "
        "release the reservation when canceling an approved order."
    ),
)
def cancel_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_order_canceler),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.cancel_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error, operation="cancel")
    return order


@router.post("/{order_id}/archive", response_model=OrderRead)
def archive_order(
    order_id: int,
    payload: OrderArchive,
    current_user: UserRead = Depends(require_order_archiver),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.archive_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order
