# Development Guide

This guide covers the working FastAPI, React, MySQL, and Alembic development
workflow.

## 1. Install Dependencies

```bash
uv sync --extra dev
```

## 2. Start the Development Database

```bash
docker compose -f docker/docker-compose.dev.yaml up -d
```

The explicitly development-only Compose file publishes MySQL and Adminer and
uses disposable example credentials. It also provisions the empty
`lab_storage_test_db` database and grants the non-root application user access.
Production uses `docker/docker-compose.yaml`, external Docker secrets, and no
published database or Adminer port.

Set local application and test connections in your shell or untracked `.env`:

```bash
export DATABASE_URL='mysql+pymysql://lab_user:lab_password@localhost:3306/lab_storage_db'
export TEST_DATABASE_URL='mysql+pymysql://lab_user:lab_password@localhost:3306/lab_storage_test_db'
```

## 3. Apply Database Migrations

Alembic revisions in `migrations/versions/` are the single schema source for
development, test, and production:

```bash
uv run alembic upgrade head
```

Run this command as a deployment step before starting new application instances.
Application startup intentionally does not create or alter database objects. To
create a future migration:

```bash
uv run alembic revision -m "describe the schema change"
```

Migrations own table definitions, status/quantity checks, indexes, and foreign
keys. The current schema rejects invalid roles, QC/order statuses, negative or
inconsistent reservations, and orphaned relationships. Relationship deletes are
explicitly restricted. Query indexes cover material search fields, order status
and ownership filters, and audit time/filter combinations.

Legacy upgrades normalize the known safe inconsistency (reservations on
non-approved orders) and fail with a named-field diagnostic when other invalid
domain values would make a new constraint unsafe to apply.

### Bootstrap the first administrator

For a new environment, inject one-time deployment secrets and run:

```bash
export BOOTSTRAP_ADMIN_USERNAME='initial_admin'
export BOOTSTRAP_ADMIN_EMAIL='initial_admin@example.com'
export BOOTSTRAP_ADMIN_PASSWORD='replace-with-a-secret-password1'
uv run python -m src.cli bootstrap-admin
```

The command creates one administrator and refuses later bootstrap attempts while
an admin exists. Use `PATCH /users/{id}/role` for subsequent role assignments;
the API prevents demotion of the last admin.

## 4. Run the API

```bash
uv run uvicorn src.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

The generated schema documents bearer authentication, the viewer/staff/admin
policy, order stock validation, and which QC/shipment modules are still planned.

## 5. Run Tests

```bash
uv run pytest
```

The test suite requires `TEST_DATABASE_URL` to identify a dedicated database.
At session start it resets that schema and runs `alembic upgrade head`; there is
no second handwritten test schema. The database itself must already exist so
pytest never needs or stores root credentials. As a guard against destructive
misconfiguration, the database name must contain `test` and the URL cannot use
the MySQL root account.

## 6. Try the First Endpoints

Health check:

```http
GET /health
GET /health/ready
```

`/health` is process liveness. `/health/ready` also verifies database
connectivity and that the applied Alembic revision matches the application.

User module:

```http
POST /users/register
POST /users/login
POST /users/logout
GET /users/me
GET /users
```

Material module:

```http
GET /materials
GET /materials/search
GET /materials/{material_id}
POST /materials
PATCH /materials/{material_id}
POST /materials/{material_id}/archive
POST /materials/{material_id}/restore
POST /materials/{material_id}/adjust-quantity
POST /materials/{material_id}/check-in
POST /materials/{material_id}/check-out
POST /materials/{material_id}/move
```

Audit module:

```http
GET /audit-logs
```

Order approval, fulfillment, and cancellation of an approved order write audit
records for their inventory effects. Each record captures available and reserved
quantities before and after the transition, and commits in the same database
transaction as the order and inventory updates.
Material archive and restore also write audit records. Restore clears every archive
metadata field from the material row; the immutable audit entry retains the history.
Archiving a terminal order requires a reason, writes `order_archived`, and cannot
be repeated or restored.

Location module:

```http
GET /locations
GET /locations/{location_id}
POST /locations
PATCH /locations/{location_id}
```

Order module:

```http
GET /orders
GET /orders/{order_id}
POST /orders
POST /orders/{order_id}/approve
POST /orders/{order_id}/reject
POST /orders/{order_id}/fulfill
POST /orders/{order_id}/cancel
```

Order stock validation policy:

- `POST /orders` validates a positive requested quantity, an existing,
  non-archived material, and sufficient unreserved stock. It does not reserve
  stock.
- `POST /orders/{order_id}/approve` performs the authoritative availability check
  under row locks. Unreserved stock is `quantity_available - quantity_reserved`.
  An insufficient order remains `submitted` and inventory is unchanged.
- `POST /orders/{order_id}/fulfill` verifies the approved reservation is still
  covered by both available and reserved quantities before deducting it. A failed
  consistency check leaves the order `approved` and inventory unchanged.
- Canceling a `submitted` order does not inspect inventory. Canceling an `approved`
  order verifies and releases its reservation. Viewers and staff may cancel only
  their own orders; admins may cancel any eligible order.
- A material cannot be archived while an approved order or reserved quantity
  exists. Fulfill or cancel the order first. Archived materials cannot be ordered
  or fulfilled. Cancellation remains available as a recovery path for a legacy
  approved order attached to an archived material and releases its reservation.

Role policy:

- Viewer: read materials/locations; create, view, cancel, and archive owned orders.
- Staff: viewer permissions plus material/location metadata management and reports.
- Admin: staff permissions plus inventory/archive operations, all-order review,
  audit logs, and the admin user list.

Location parent changes run under a database transaction lock, walk the proposed
parent's ancestor chain, and return `409` if the change would introduce either a
direct or indirect cycle. This prevents concurrent changes from jointly creating
a cycle.

Order list supports these optional query parameters:

```text
status
material_id
requested_by_user_id
reviewed_by_user_id
page
size
```

Report module:

```http
GET /reports/low-stock
GET /reports/pending-orders
GET /reports/recent-inventory-activity
GET /reports/materials-by-location
```

Material search supports these optional query parameters:

```text
keyword
material_type
source
qc_status
availability_status
location_id
low_stock
include_archived
page
size
```

Recent inventory activity report supports these optional query parameters:

```text
user_id
material_id
operation_type
limit
```

Audit logs support these optional query parameters:

```text
user_id
material_id
operation_type
page
size
```

`GET /materials`, `GET /materials/search`, `GET /orders`, `GET /locations`,
`GET /audit-logs`, and `GET /users` use page-number pagination. `page` starts at 1, `size` defaults
to 25 and is capped at 100. Responses have this shape:

```json
{
  "items": [],
  "page": 1,
  "size": 25,
  "total": 0,
  "pages": 0
}
```

Protected endpoints use the authorization header:

```http
Authorization: Bearer <token>
```

Every error, including authentication, authorization, validation, routing, and
business-rule failures, uses this response structure:

```json
{
  "error": {
    "code": "MATERIAL_NOT_FOUND",
    "message": "Material not found"
  }
}
```

Clients should branch on `error.code`, not on the human-readable message.
Validation responses also include `error.details` with field-level entries.

## Project Shape

```text
src/
  main.py              # Creates the FastAPI app and registers routers.
  auth/                # Token validation and reusable auth dependencies.
  audit/               # Admin inventory audit log review endpoints.
  core/config.py       # Reads environment configuration.
  db/connection.py     # Creates the SQLAlchemy database session.
  ../migrations/       # Alembic schema source used in every environment.
  health/router.py     # Minimal API health check.
  location/            # Storage location CRUD endpoints.
  material/            # Material CRUD, search, archive, and restore endpoints.
  order/               # Material request, approval, fulfillment, and cancellation endpoints.
  report/              # Dashboard-style inventory and order report endpoints.
  user/                # User registration, login, logout, and profile endpoints.
  utils/security.py    # Password hashing and token helper functions.
  utils/constant.py    # Shared role constants.
```

When adding a new feature, follow the same pattern:

1. Define request and response models in `schemas.py`.
2. Put database logic in `service.py`.
3. Put FastAPI routes in `router.py`.
4. Register the router in `src/main.py`.
