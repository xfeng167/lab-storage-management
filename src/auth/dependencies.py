from collections.abc import Callable

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.core.errors import forbidden, unauthorized
from src.user.schemas import UserRead
from src.auth import service
from src.utils.constant import (
    PERMISSION_AUDIT_READ,
    PERMISSION_CATALOG_MANAGE,
    PERMISSION_INVENTORY_MANAGE,
    PERMISSION_LOCATION_READ,
    PERMISSION_MATERIAL_READ,
    PERMISSION_ORDER_ARCHIVE_OWN,
    PERMISSION_ORDER_CANCEL_OWN,
    PERMISSION_ORDER_CREATE,
    PERMISSION_ORDER_READ_OWN,
    PERMISSION_ORDER_REVIEW,
    PERMISSION_REPORT_READ,
    PERMISSION_USER_MANAGE,
    ROLE_PERMISSIONS,
    role_has_permission,
)


bearer_auth = HTTPBearer(
    auto_error=False,
    bearerFormat="opaque token",
    description="Token returned by POST /users/login.",
    scheme_name="BearerAuth",
)


def get_bearer_token(
    request: Request,
    _credentials: HTTPAuthorizationCredentials | None = Security(bearer_auth),
) -> str:
    # Read the raw header after registering HTTPBearer so the existing business
    # error codes remain stable for missing, malformed, and empty bearer values.
    authorization = request.headers.get("Authorization")
    if authorization is None:
        raise unauthorized("AUTH_HEADER_MISSING", "Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise unauthorized("AUTH_HEADER_INVALID", "Invalid authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise unauthorized("AUTH_TOKEN_MISSING", "Missing bearer token")

    return token

def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> UserRead:
    user = service.get_user_from_token(token, db)

    if user is None:
        raise unauthorized("AUTH_TOKEN_INVALID", "Invalid or expired token")
    if user.role not in ROLE_PERMISSIONS:
        raise forbidden("ROLE_INVALID", "User role is not recognized")
    return user


def require_permission(permission: str) -> Callable[..., UserRead]:
    def permission_dependency(
        current_user: UserRead = Depends(get_current_user),
    ) -> UserRead:
        if not role_has_permission(current_user.role, permission):
            raise forbidden(
                "PERMISSION_DENIED",
                "User does not have sufficient privileges",
            )
        return current_user

    return permission_dependency


require_material_reader = require_permission(PERMISSION_MATERIAL_READ)
require_location_reader = require_permission(PERMISSION_LOCATION_READ)
require_order_reader = require_permission(PERMISSION_ORDER_READ_OWN)
require_order_creator = require_permission(PERMISSION_ORDER_CREATE)
require_order_canceler = require_permission(PERMISSION_ORDER_CANCEL_OWN)
require_order_archiver = require_permission(PERMISSION_ORDER_ARCHIVE_OWN)
require_catalog_manager = require_permission(PERMISSION_CATALOG_MANAGE)
require_report_reader = require_permission(PERMISSION_REPORT_READ)
require_inventory_manager = require_permission(PERMISSION_INVENTORY_MANAGE)
require_order_reviewer = require_permission(PERMISSION_ORDER_REVIEW)
require_audit_reader = require_permission(PERMISSION_AUDIT_READ)
require_user_manager = require_permission(PERMISSION_USER_MANAGE)
