from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.errors import business_error
from src.db.connection import get_db

router = APIRouter(tags=["health"])
EXPECTED_SCHEMA_REVISION = "20260812_0004"


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1")).scalar_one()
        migration = db.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise business_error(
            "SERVICE_NOT_READY",
            "Database is unavailable or has not been migrated",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    if migration != EXPECTED_SCHEMA_REVISION:
        raise business_error(
            "SERVICE_NOT_READY",
            "Database schema is not at the application revision",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return {"status": "ready", "database": "ok", "migration": migration}
