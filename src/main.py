from fastapi import FastAPI
from src.audit.router import router as audit_router
from src.core.config import settings
from src.db.connection import engine
from src.db.schema import ensure_database_schema
from src.health.router import router as health_router
from src.location.router import router as location_router
from src.test_table.router import router as test_table_router
from src.user.router import router as user_router
from src.material.router import router as material_router
from src.order.router import router as order_router
from src.report.router import router as report_router

def create_app() -> FastAPI:
    ensure_database_schema(engine)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    app.include_router(health_router)
    app.include_router(test_table_router, prefix="/test-table", tags=["test-table", "deprecated"])
    app.include_router(user_router, prefix="/users", tags=["users"])
    app.include_router(material_router, prefix="/materials", tags=["materials"])
    app.include_router(location_router, prefix="/locations", tags=["locations"])
    app.include_router(order_router, prefix="/orders", tags=["orders"])
    app.include_router(report_router, prefix="/reports", tags=["reports"])
    app.include_router(audit_router, tags=["audit"])
    return app

app = create_app()
