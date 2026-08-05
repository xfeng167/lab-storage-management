from fastapi import FastAPI

from src.audit.router import router as audit_router
from src.core.config import settings
from src.health.router import router as health_router
from src.location.router import router as location_router
from src.test_table.router import router as test_table_router
from src.user.router import router as user_router
from src.material.router import router as material_router

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    app.include_router(health_router)
    app.include_router(test_table_router, prefix="/test-table", tags=["test-table"])
    app.include_router(user_router, prefix="/users", tags=["users"])
    app.include_router(material_router, prefix="/materials", tags=["materials"])
    app.include_router(location_router, prefix="/locations", tags=["locations"])
    app.include_router(audit_router, tags=["audit"])
    return app

app = create_app()
