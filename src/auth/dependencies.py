from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.user.schemas import UserRead
from src.auth import service
from src.utils.constant import ROLE_ADMIN, ROLE_STAFF


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    return token

def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> UserRead:
    user = service.get_user_from_token(token, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user

def require_staff_user(current_user: UserRead = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead | None:
    if current_user.role not in [ROLE_STAFF, ROLE_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have sufficient privileges",
        )
    return current_user

def require_admin_user(current_user: UserRead = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead | None:
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have sufficient privileges",
        )
    return current_user


