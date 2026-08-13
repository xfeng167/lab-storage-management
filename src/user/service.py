from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.pagination import Page, build_page, page_offset
from src.user.schemas import (
    PasswordChange,
    Token,
    UserCreate,
    UserDirectoryRead,
    UserLogin,
    UserProfileUpdate,
    UserRead,
)
from src.utils.constant import ROLE_ADMIN, ROLE_VIEWER
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


def _record_failed_login(db: Session, username: str, now: datetime) -> None:
    window_cutoff = now - timedelta(minutes=settings.login_window_minutes)
    locked_until = now + timedelta(minutes=settings.login_lock_minutes)
    db.execute(
        text(
            """
            INSERT INTO login_throttle (
                username,
                failed_attempts,
                window_started_at,
                locked_until
            )
            VALUES (:username, 1, :now, NULL)
            ON DUPLICATE KEY UPDATE
                failed_attempts = IF(
                    window_started_at < :window_cutoff,
                    1,
                    failed_attempts + 1
                ),
                window_started_at = IF(
                    window_started_at < :window_cutoff,
                    :now,
                    window_started_at
                ),
                locked_until = IF(
                    failed_attempts >= :max_attempts,
                    :locked_until,
                    NULL
                )
            """
        ),
        {
            "username": username,
            "now": now,
            "window_cutoff": window_cutoff,
            "max_attempts": settings.login_max_attempts,
            "locked_until": locked_until,
        },
    )


def login_user(db: Session, payload: UserLogin) -> tuple[UserRead, str] | str:
    now = datetime.utcnow()
    throttle = db.execute(
        text(
            """
            SELECT locked_until
            FROM login_throttle
            WHERE username = :username
            FOR UPDATE
            """
        ),
        {"username": payload.username},
    ).mappings().first()
    if throttle is not None and throttle["locked_until"] is not None:
        if throttle["locked_until"] > now:
            db.commit()
            return "rate_limited"

    row = db.execute(
        text("SELECT id, username, email, password_hash, role, profile_picture FROM users WHERE username = :username"),
        {"username": payload.username},
    ).mappings().first()
    if row is None or not verify_password(payload.password, row["password_hash"]):
        _record_failed_login(db, payload.username, now)
        db.commit()
        return "invalid_credentials"

    db.execute(
        text("DELETE FROM login_throttle WHERE username = :username"),
        {"username": payload.username},
    )
    db.execute(
        text("DELETE FROM token_table WHERE created_at < :cutoff"),
        {"cutoff": now - timedelta(minutes=settings.token_ttl_minutes)},
    )
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

def list_users(db: Session, page: int = 1, size: int = 25) -> Page[UserDirectoryRead]:
    total = db.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    rows = db.execute(
        text(
            """
            SELECT id, username, email, role
            FROM users
            ORDER BY username, id
            LIMIT :size OFFSET :offset
            """
        ),
        {"size": size, "offset": page_offset(page, size)},
    ).mappings().all()
    return build_page(
        [UserDirectoryRead(**row) for row in rows],
        page=page,
        size=size,
        total=total,
    )

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


def change_password(db: Session, user_id: int, payload: PasswordChange) -> bool:
    row = db.execute(
        text("SELECT password_hash FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if row is None or not verify_password(payload.current_password, row["password_hash"]):
        return False

    db.execute(
        text("UPDATE users SET password_hash = :password_hash WHERE id = :user_id"),
        {"password_hash": hash_password(payload.new_password), "user_id": user_id},
    )
    db.execute(
        text("DELETE FROM token_table WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    db.commit()
    return True


def update_user_role(
    db: Session,
    user_id: int,
    role: str,
) -> tuple[UserDirectoryRead | None, str | None]:
    lock_name = "lab_storage_admin_roles"
    acquired = db.execute(
        text("SELECT GET_LOCK(:lock_name, 10)"),
        {"lock_name": lock_name},
    ).scalar_one()
    if acquired != 1:
        return None, "lock_timeout"
    try:
        user = db.execute(
            text("SELECT id, username, email, role FROM users WHERE id = :user_id FOR UPDATE"),
            {"user_id": user_id},
        ).mappings().first()
        if user is None:
            return None, "not_found"
        if user["role"] == ROLE_ADMIN and role != ROLE_ADMIN:
            admin_count = db.execute(
                text("SELECT COUNT(*) FROM users WHERE role = :role"),
                {"role": ROLE_ADMIN},
            ).scalar_one()
            if admin_count <= 1:
                return None, "last_admin"

        db.execute(
            text("UPDATE users SET role = :role WHERE id = :user_id"),
            {"role": role, "user_id": user_id},
        )
        db.execute(
            text("DELETE FROM token_table WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        db.commit()
        return UserDirectoryRead(
            id=user["id"], username=user["username"], email=user["email"], role=role,
        ), None
    finally:
        db.execute(
            text("SELECT RELEASE_LOCK(:lock_name)"),
            {"lock_name": lock_name},
        )


def bootstrap_admin(
    db: Session,
    payload: UserCreate,
) -> tuple[UserRead | None, str | None]:
    lock_name = "lab_storage_bootstrap_admin"
    acquired = db.execute(
        text("SELECT GET_LOCK(:lock_name, 10)"),
        {"lock_name": lock_name},
    ).scalar_one()
    if acquired != 1:
        return None, "lock_timeout"
    try:
        if db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).first():
            return None, "admin_exists"
        if db.execute(
            text("SELECT id FROM users WHERE username = :username OR email = :email"),
            {"username": payload.username, "email": payload.email},
        ).first():
            return None, "identity_exists"

        db.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (:username, :email, :password_hash, :role)
                """
            ),
            {
                "username": payload.username,
                "email": payload.email,
                "password_hash": hash_password(payload.password),
                "role": ROLE_ADMIN,
            },
        )
        user_id = db.execute(text("SELECT LAST_INSERT_ID()")) .scalar_one()
        db.commit()
        return UserRead(
            id=user_id,
            username=payload.username,
            email=payload.email,
            role=ROLE_ADMIN,
            profile_picture=None,
        ), None
    finally:
        db.execute(
            text("SELECT RELEASE_LOCK(:lock_name)"),
            {"lock_name": lock_name},
        )
