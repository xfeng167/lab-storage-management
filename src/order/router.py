from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, require_admin_user
from src.db.connection import get_db
from src.order import service
from src.order.schemas import OrderCreate, OrderRead, OrderReview
from src.user.schemas import UserRead

router = APIRouter()


def _raise_order_error(error: str | None) -> None:
    if error in {"not_found", "material_not_found"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order or material not found",
        )
    if error == "invalid_status":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order status does not allow this operation",
        )
    if error == "archived_material":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived material cannot be ordered",
        )
    if error == "insufficient_quantity":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient quantity available",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Order operation failed",
    )


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.create_order(db, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order


@router.get("", response_model=list[OrderRead])
def list_orders(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    return service.list_orders(db, current_user)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order = service.get_order(db, order_id, current_user)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


@router.post("/{order_id}/approve", response_model=OrderRead)
def approve_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.approve_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order


@router.post("/{order_id}/reject", response_model=OrderRead)
def reject_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.reject_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order


@router.post("/{order_id}/fulfill", response_model=OrderRead)
def fulfill_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.fulfill_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int,
    payload: OrderReview | None = None,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderRead:
    order, error = service.cancel_order(db, order_id, current_user, payload)
    if order is None:
        _raise_order_error(error)
    return order
