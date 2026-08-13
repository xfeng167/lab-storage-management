from sqlalchemy import text
from sqlalchemy.orm import Session

from src.user.schemas import UserCreate, UserLogin, UserProfileUpdate, UserRead, Token
from src.utils.constant import ROLE_VIEWER
from src.utils.security import generate_token, hash_password, hash_token, verify_password


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
            INSERT INTO users (username, email, password_hash, profile_picture)
            VALUES (:username, :email, :password_hash, :profile_picture)
            """
        ),
        {
            "username": payload.username,
            "email": payload.email,
            "password_hash": password_hash,
            "profile_picture": None,
        },
    )
    user_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    db.commit()

    return UserRead(id=user_id, username=payload.username, email=payload.email, role=ROLE_VIEWER, profile_picture=None)  # Default role is ROLE_VIEWER


def login_user(db: Session, payload: UserLogin) -> tuple[UserRead, str] | None:
    row = db.execute(
        text("SELECT id, username, email, password_hash, role, profile_picture FROM users WHERE username = :username"),
        {"username": payload.username},
    ).mappings().first()
    if row is None:
        return None

    if not verify_password(payload.password, row["password_hash"]):
        return None
    token = generate_token()
    token_hash = hash_token(token)
    db.execute(
            text(
                """
                INSERT INTO token_table (token, created_at, user_id)
                VALUES (:token, CURRENT_TIMESTAMP, :user_id)
                """
            ),
            {
                "token": token_hash,
                "user_id": row["id"],
            },
        )
    db.commit()
    user = UserRead(id=row["id"], username=row["username"], email=row["email"], role=row["role"], profile_picture=row["profile_picture"])
    return user, token

def list_users(db: Session) -> list[UserRead]:
    rows = db.execute(text("SELECT id, username, email, role, profile_picture FROM users")).mappings().all()
    return [UserRead(id=row["id"], username=row["username"], email=row["email"], role=row["role"], profile_picture=row["profile_picture"]) for row in rows]

def logout_user(db: Session, payload: Token) -> bool:
    result = db.execute(
        text("DELETE FROM token_table WHERE token = :token"),
        {"token": hash_token(payload.token)},
    )
    db.commit()
    return result.rowcount > 0 

def get_user(db: Session, user_id: int) -> UserRead | None:
    row = db.execute(
        text("SELECT id, username, email, role, profile_picture FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        return None
    return UserRead(id=row["id"], username=row["username"], email=row["email"], role=row["role"], profile_picture=row["profile_picture"])


def update_profile(db: Session, user_id: int, payload: UserProfileUpdate) -> UserRead | None:
    existing_user = db.execute(
        text(
            """
            SELECT id
            FROM users
            WHERE (username = :username OR email = :email)
            AND id != :user_id
            """
        ),
        {"username": payload.username, "email": payload.email, "user_id": user_id},
    ).first()
    if existing_user is not None:
        return None

    db.execute(
        text(
            """
            UPDATE users
            SET username = :username,
                email = :email,
                profile_picture = :profile_picture
            WHERE id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "username": payload.username,
            "email": payload.email,
            "profile_picture": payload.profile_picture,
        },
    )
    db.commit()

    return get_user(db, user_id)


