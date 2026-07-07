from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.user import service
from src.user.schemas import LoginResponse, LogoutResponse, UserCreate, UserLogin, UserRead

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
def logout_user() -> LogoutResponse:
    return LogoutResponse(message="Logout received. The client can forget the current token.")
