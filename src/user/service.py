from sqlalchemy import text
from sqlalchemy.orm import Session

from src.user.schemas import UserCreate, UserLogin, UserRead, Token
from src.utils.security import create_demo_token, hash_password, verify_password


def create_user(db: Session, payload: UserCreate) -> UserRead | None:
    if len(payload.username) < 1 or len(payload.password) < 6 or len(payload.username) > 80 or len(payload.email) > 255 or len(payload.password) > 255:
        return None
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
    token = create_demo_token()
    db.execute(
            text(
                """
                INSERT INTO token_table (token, created_at, user_id)
                VALUES (:token, CURRENT_TIMESTAMP, :user_id)
                """
            ),
            {
                "token": token,
                "user_id": row["id"],
            },
        )
    db.commit()
    user = UserRead(id=row["id"], username=row["username"], email=row["email"])
    return user, token

def list_users(db: Session) -> list[UserRead]:
    rows = db.execute(text("SELECT id, username, email FROM users")).mappings().all()
    return [UserRead(id=row["id"], username=row["username"], email=row["email"]) for row in rows]

def logout_user(db: Session, payload: Token) -> bool:
    result = db.execute(
        text("DELETE FROM token_table WHERE token = :token"),
        {"token": payload.token},
    )
    db.commit()
    return result.rowcount > 0 
   

