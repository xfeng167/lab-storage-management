from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.audit.router import router as audit_router
from src.core.config import settings
from src.core.errors import DEFAULT_ERROR_RESPONSES, install_error_handlers
from src.health.router import router as health_router
from src.location.router import router as location_router
from src.user.router import router as user_router
from src.material.router import router as material_router
from src.order.router import router as order_router
from src.report.router import router as report_router


API_DESCRIPTION = """
Inventory, storage-location, material-request, reporting, and audit APIs for the
lab storage application.

### Authentication

`POST /users/register` creates a viewer account. `POST /users/login` returns an
opaque token. Send that token as `Authorization: Bearer <token>` to protected
operations. `GET /users/me`, `PATCH /users/me`, and `POST /users/me/password`
manage the signed-in account. `POST /users/logout` retires the token supplied in
its request body. Password and role changes revoke all active tokens for the
affected account. Login failures are rate limited.

### Roles

* **Viewer** — read materials and locations; create orders; read, cancel, or
  archive eligible owned orders.
* **Staff** — viewer permissions plus material/location metadata management and
  operational reports.
* **Admin** — staff permissions plus inventory and material archive operations,
  review of all orders, audit logs, and user role management.

### Stock validation

Order submission validates current unreserved stock but does not reserve it.
Approval is authoritative: it locks the order and material and requires
`quantity_available - quantity_reserved >= requested_quantity` before reserving
stock atomically. Fulfillment revalidates the reservation before deducting both
available and reserved quantities. Canceling an approved order releases its
reservation. Availability status is derived at query time from unreserved stock.

### Archive policy

A material with approved orders or reserved stock cannot be archived until those
orders are fulfilled or canceled. Material restore clears row-level archive
metadata while audit history remains. Only terminal orders can be archived; an
order archive requires a reason, is audited, and cannot be overwritten or restored.

### Planned features

QC flags, QC execution, and shipment records are planned modules and are not API
operations in this version. Their design is gated on stable inventory and order
workflows.
"""

OPENAPI_TAGS = [
    {"name": "health", "description": "Service readiness."},
    {"name": "users", "description": "Authentication, profiles, and admin user listing."},
    {"name": "materials", "description": "Material catalogue, inventory, and archive operations."},
    {"name": "locations", "description": "Cycle-safe storage hierarchy management."},
    {"name": "orders", "description": "Request, reservation, review, fulfillment, and cancellation."},
    {"name": "reports", "description": "Staff and admin operational reports."},
    {"name": "audit", "description": "Admin access to immutable inventory audit records."},
]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        summary="Lab inventory and material request API",
        description=API_DESCRIPTION,
        version="0.1.0",
        debug=settings.debug,
        openapi_tags=OPENAPI_TAGS,
        responses=DEFAULT_ERROR_RESPONSES,
    )
    install_error_handlers(app)
    if settings.allowed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_cors_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip()[:128]
        if not request_id:
            request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health_router)
    app.include_router(user_router, prefix="/users", tags=["users"])
    app.include_router(material_router, prefix="/materials", tags=["materials"])
    app.include_router(location_router, prefix="/locations", tags=["locations"])
    app.include_router(order_router, prefix="/orders", tags=["orders"])
    app.include_router(report_router, prefix="/reports", tags=["reports"])
    app.include_router(audit_router, tags=["audit"])
    return app

app = create_app()
