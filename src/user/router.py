from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.user import service
from src.user.schemas import LoginResponse, LogoutResponse, UserCreate, UserLogin, UserRead, Token
from src.auth.dependencies import get_current_user, require_admin_user

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    user = service.create_user(db, payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )
    return user


@router.post("/login", response_model=LoginResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> LoginResponse:
    login_result = service.login_user(db, payload)
    if login_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user, token = login_result
    return LoginResponse(user=user, token=token)


@router.post("/logout", response_model=LogoutResponse)
def logout_user(payload: Token, db: Session = Depends(get_db)) -> LogoutResponse:
    logout_result = service.logout_user(db, payload)
    if not logout_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed",
        )
    return LogoutResponse(message="Logout received. The client can forget the current token.")

@router.get("", response_model=list[UserRead])
def list_users(
    current_user: UserRead = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    return service.list_users(db)


@router.get("/me", response_model=UserRead)
def check_user(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    return current_user

