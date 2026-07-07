from sqlalchemy import text
from sqlalchemy.orm import Session

from src.user.schemas import UserCreate, UserLogin, UserRead
from src.utils.security import create_demo_token, hash_password, verify_password


def create_user(db: Session, payload: UserCreate) -> UserRead | None:
    existing_user = db.execute(
        text("SELECT id FROM users WHERE username = :username OR email = :email"),
        {"username": payload.username, "email": payload.email},
    ).first()
    if existing_user is not None:
        return None

    password_hash = hash_password(payload.password)
    db.execute(
        text(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (:username, :email, :password_hash)
            """
        ),
        {
            "username": payload.username,
            "email": payload.email,
            "password_hash": password_hash,
        },
    )
    user_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()

    return UserRead(id=user_id, username=payload.username, email=payload.email)


def login_user(db: Session, payload: UserLogin) -> tuple[UserRead, str] | None:
    row = db.execute(
        text("SELECT id, username, email, password_hash FROM users WHERE username = :username"),
        {"username": payload.username},
    ).mappings().first()
    if row is None:
        return None

    if not verify_password(payload.password, row["password_hash"]):
        return None

    user = UserRead(id=row["id"], username=row["username"], email=row["email"])
    return user, create_demo_token()
