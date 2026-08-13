import src
from src.db.connection import get_db


from fastapi.params import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session


from datetime import datetime, timedelta

from src.user.schemas import UserRead
from src.user.service import get_user
from src.utils.constant import ROLE_ADMIN, ROLE_STAFF
from src.utils.security import hash_token


def verify_token(token: str, db: Session = Depends(get_db)) -> tuple[bool, int | None]:
    token = hash_token(token)
    result = db.execute(
        text("SELECT user_id, created_at FROM token_table WHERE token = :token"),
        {"token": token},
    ).mappings().first()

    if result is None:
        return False, None
    
    user_id = result["user_id"]

    if result["created_at"] is None:
        return False, None
    if result["user_id"] is None:
        return False, None
    if result["created_at"] < (datetime.utcnow() - timedelta(hours=1)):
        return False, None
    return True, user_id

def get_user_from_token(token: str, db: Session = Depends(get_db)) -> UserRead | None:
    result, user_id = verify_token(token, db)
    if not result:
        return None
    return get_user(db, user_id)


