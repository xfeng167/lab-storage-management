from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.core.errors import bad_request, conflict, not_found, too_many_requests, unauthorized
from src.core.config import settings
from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page
from src.user import service
from src.user.schemas import (
    LoginResponse,
    LogoutResponse,
    PasswordChange,
    PasswordChangeResponse,
    Token,
    UserCreate,
    UserDirectoryRead,
    UserLogin,
    UserProfileUpdate,
    UserRead,
    UserRoleUpdate,
)
from src.auth.dependencies import get_current_user, require_user_manager

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a viewer account",
    description="Create a public account. New accounts always receive the viewer role.",
)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    user = service.create_user(db, payload)
    if user is None:
        raise conflict("USER_IDENTITY_CONFLICT", "Username or email already exists")
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in and issue a bearer token",
    description=(
        "Authenticate with username and password. Use the returned opaque token "
        "as `Authorization: Bearer <token>` on protected operations."
    ),
)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> LoginResponse:
    login_result = service.login_user(db, payload)
    if login_result == "rate_limited":
        raise too_many_requests(
            "LOGIN_RATE_LIMITED",
            "Too many failed login attempts; try again later",
            retry_after=settings.login_lock_minutes * 60,
        )
    if login_result == "invalid_credentials":
        raise unauthorized("INVALID_CREDENTIALS", "Invalid username or password")

    user, token = login_result
    return LoginResponse(user=user, token=token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out a token",
    description="Retire the opaque token supplied in the request body.",
)
def logout_user(payload: Token, db: Session = Depends(get_db)) -> LogoutResponse:
    logout_result = service.logout_user(db, payload)
    if not logout_result:
        raise bad_request("LOGOUT_FAILED", "Logout failed")
    return LogoutResponse(message="Logout received. The client can forget the current token.")

@router.get("", response_model=Page[UserDirectoryRead])
def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: UserRead = Depends(require_user_manager),
    db: Session = Depends(get_db),
) -> Page[UserDirectoryRead]:
    return service.list_users(db, page=page, size=size)


@router.patch("/{user_id}/role", response_model=UserDirectoryRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: UserRead = Depends(require_user_manager),
    db: Session = Depends(get_db),
) -> UserDirectoryRead:
    user, error = service.update_user_role(db, user_id, payload.role)
    if error == "not_found":
        raise not_found("USER_NOT_FOUND", "User not found")
    if error == "last_admin":
        raise conflict("LAST_ADMIN_REQUIRED", "The last admin cannot be demoted")
    if error == "lock_timeout":
        raise conflict("USER_ROLE_UPDATE_BUSY", "User roles are being updated; retry the request")
    if user is None:
        raise bad_request("USER_ROLE_UPDATE_FAILED", "User role could not be updated")
    return user


@router.get("/me", response_model=UserRead)
def check_user(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user_profile(
    payload: UserProfileUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    user = service.update_profile(db, current_user.id, payload)
    if user is None:
        raise conflict("USER_IDENTITY_CONFLICT", "Username or email already exists")
    return user


@router.post("/me/password", response_model=PasswordChangeResponse)
def change_current_user_password(
    payload: PasswordChange,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PasswordChangeResponse:
    if not service.change_password(db, current_user.id, payload):
        raise bad_request("CURRENT_PASSWORD_INVALID", "Current password is incorrect.")
    return PasswordChangeResponse(message="Password updated successfully.")
