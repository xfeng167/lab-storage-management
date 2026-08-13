# Lab Storage Management API

FastAPI backend for managing mixed research lab materials, storage locations,
quantity-based inventory, material requests, material QC status, and audit-safe
inventory operations.

This repository contains the working backend and frontend application contract.

## Product Vision

Research labs often track materials across freezers, shelves, boxes, spreadsheets,
and manual request channels. This project centralizes the implemented workflows
into one backend API that supports:

- Searching and reviewing lab material records.
- Managing quantity-based inventory for mixed material types.
- Requesting materials from available stock.
- Approving, rejecting, and fulfilling requests.
- Storing a QC status on each material.
- Preserving audit history for sensitive inventory operations.
- Restricting actions by user role.

## Repository Scope

This repo contains the backend API and its standalone React frontend.

- Backend: FastAPI application.
- Database: MySQL.
- API style: REST.
- Frontend: React application in `front-end/`.

The React frontend consumes the API through the routes documented below and in
the generated OpenAPI UI at `/docs`.

## Intended Users

| Role | Permission Level | Primary Needs |
| --- | --- | --- |
| Vendor / requester | Viewer | Browse inventory and create, view, cancel, or archive their own requests. |
| Research operations | Staff | Viewer capabilities plus material/location metadata and operational reports. |
| Data management | Admin | Staff capabilities plus inventory, order review, archive, audit, and the admin user list. |

Permission priority:

```text
Viewer < Staff < Admin
```

## Material Scope

The system supports mixed lab materials through one shared material model, with
material-specific details captured through fields such as `material_type`, `unit`,
`storage_condition`, and notes.

Example material types:

- Biological specimens.
- Chemicals and reagents.
- Lab consumables.
- Controls or reference materials.
- Other research materials tracked by quantity.

Separate tables are not created for every material type.

## Core Workflows

### Inventory Discovery

Users can search for stored materials by identifiers, material type, storage location, QC status, availability, and other indexed fields.

Implemented behavior:

- Inventory dashboard metrics.
- Searchable material list.
- Material detail endpoint.
- Quantity and availability visibility.
- Read-only views for viewer-level users.

### Material Requests

Research users can request a quantity of available material. Admin users review, approve, reject, and fulfill those requests.

Implemented behavior:

- Submit a material request with requested quantity and notes.
- Prevent requests for archived materials.
- Reject requests above current unreserved stock; do not reserve inventory at
  submission time.
- Track request status.
- Reserve inventory after approval.
- Reduce inventory after fulfillment.

Shipment records are planned and are not part of the current order workflow.

### Catalogue and Inventory Operations

Staff users maintain material and location metadata. Admin users additionally
maintain inventory balances and archive state.

Implemented behavior:

- Create material records.
- Update material metadata.
- Adjust available quantity.
- Move materials between storage locations.
- Check materials in or out.
- Archive materials instead of permanently deleting them.
- Record sensitive changes in audit logs.

### QC and Shipment Planning

Materials currently carry a `qc_status` value that staff can edit as catalogue
metadata. Dedicated QC flags, QC execution, and shipment records are planned,
not implemented. They will be evaluated only after the inventory and order
stability gates in [`docs/qc-and-shipments-plan.md`](docs/qc-and-shipments-plan.md)
are satisfied.

Planned capabilities:

- View QC flags.
- Trigger QC checks.
- Update QC status.
- Identify missing or inconsistent fields.
- Preserve audit history for manual corrections.
- Create shipment records for fulfilled orders and audit each shipment transition.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3, FastAPI |
| Database | MySQL |
| Database Layer | SQLAlchemy sessions and SQL text |
| Migrations | Alembic |
| Validation | Pydantic |
| Authentication | Token-based authentication |
| API Documentation | FastAPI OpenAPI docs |
| Testing | Pytest |

## Database Lifecycle and Production Configuration

Alembic revisions under `migrations/versions/` are the only schema source for
development, tests, and production. Apply migrations before starting the API:

```bash
uv run alembic upgrade head
```

FastAPI startup never issues schema-changing DDL. Pytest also invokes this same
migration chain against the dedicated database supplied by `TEST_DATABASE_URL`.

The database enforces user roles, QC/order status domains, positive order
quantities, non-negative stock, reservation consistency, and all declared
relationships. Common material, order, and audit filters use migration-managed
single-column or composite indexes. Foreign keys use explicit `RESTRICT` delete
behavior so operational and audit history cannot be orphaned.

`DEBUG` defaults to `false`, and `DATABASE_URL` is required rather than carrying
built-in credentials. Deployments must inject it from their secret manager. The
production database Compose definition uses external Docker secrets and does not
publish MySQL or Adminer ports; local-only conveniences live in
`docker/docker-compose.dev.yaml`.

After migrating a new deployment, create the first administrator exactly once
from secret-backed `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_EMAIL`, and
`BOOTSTRAP_ADMIN_PASSWORD` values:

```bash
uv run python -m src.cli bootstrap-admin
```

The command refuses to overwrite an identity or run after an administrator
exists. Administrators can subsequently assign roles through
`PATCH /users/{id}/role`; the last admin cannot be demoted. Role and password
changes revoke every active token for that account.

## Error Contract

Every non-success API response uses the same envelope:

```json
{
  "error": {
    "code": "ORDER_STATUS_CONFLICT",
    "message": "Order status does not allow this operation",
    "details": null
  }
}
```

`code` is the stable machine-readable business code and `message` is safe for
display. `details` is included only when useful, such as field-level validation
failures. Statuses are consistent: `400` malformed operations, `401`
authentication, `403` permission, `404` missing resources, `409` state or stock
conflicts, `422` request validation, and `500` unexpected failures.

## System Architecture

```text
External frontend client
        |
        v
FastAPI REST API
        |
        v
Service layer and business rules
        |
        v
SQLAlchemy database access
        |
        v
MySQL database
```

Implemented backend modules:

- `auth`: registration, login, logout, token validation, role checks.
- `users`: account and permission management.
- `materials`: material CRUD, archive lifecycle, material detail records.
- `locations`: storage hierarchy and location metadata.
- `inventory`: quantity adjustments, reservation, check-in, check-out, movement, availability.
- `orders`: request submission, review, approval, rejection, fulfillment, and outcomes.
- `audit`: immutable operation logs.

Planned modules are `qc` for flagging and consistency runs and `shipments` for
tracking fulfilled requests. See the gated design plan linked above.

## Business Rules

The current API enforces these rules:

- A user cannot request an archived material.
- Submission validates that the requested quantity is positive, the material
  exists and is active, and unreserved stock covers the request. It does not
  reserve inventory.
- Approval is the authoritative stock check. It locks the order and material,
  requires `quantity_available - quantity_reserved >= requested_quantity`, and
  reserves the requested quantity in the same transaction.
- Fulfillment revalidates that both available and reserved inventory cover the
  order's reservation, then subtracts the reservation from both quantities.
- Rejecting or canceling a request releases any reserved quantity.
- Quantity changes and order transitions lock affected rows and commit atomically so concurrent requests cannot over-reserve or apply a reservation twice.
- Archived materials remain in the database but are hidden from normal active inventory searches.
- A material with an approved order or any reserved stock cannot be archived.
  The order must be fulfilled or canceled first. Cancellation releases the
  reservation and writes its inventory audit entry.
- Archiving and restoring a material write lifecycle audit entries. Restore clears
  `archived_at`, `archived_by_user_id`, and `archive_reason` while retaining the
  archive history in the audit log.
- `availability_status` is not stored. Every material read and availability filter
  derives it from unreserved stock (`quantity_available - quantity_reserved`):
  `unavailable` at zero, `low_stock` at or below `minimum_quantity`, otherwise
  `available`.
- Viewers may create orders and cancel or archive their own eligible orders, but
  cannot change catalogue metadata, inventory, other users' requests, or reviews.
- Staff inherit viewer actions and may create/edit material and location metadata
  and read reports. They cannot adjust inventory, archive materials, review orders,
  read audit logs, or manage users.
- Admins inherit staff actions and may perform inventory/archive operations, review
  all orders, read audit logs, and manage user roles.
- Terminal orders may be archived only with a nonblank reason. Order archive is
  immutable (there is no restore endpoint), duplicate attempts are rejected, and
  the original actor, timestamp, reason, and audit entry remain unchanged.

## API

### Authentication

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/users/register` | Create a viewer account. |
| `POST` | `/users/login` | Authenticate a user and return a token. |
| `POST` | `/users/logout` | Retire the token supplied in the request body. |
| `GET` | `/users/me` | Read the bearer-token account. |
| `PATCH` | `/users/me` | Update the bearer-token account profile. |
| `POST` | `/users/me/password` | Change the bearer-token account password. |
| `GET` | `/users` | Admin-only user list. |
| `PATCH` | `/users/{id}/role` | Admin-only role assignment. |

Tokens expire after `TOKEN_TTL_MINUTES` (60 by default). Login failures are
persisted and rate limited through the configurable `LOGIN_*` settings; `429`
responses include `Retry-After`.

Except for registration, login, logout, health, and generated documentation,
endpoints require the token returned by login:

```http
Authorization: Bearer <token>
```

Login request:

```json
{
  "username": "research_user",
  "password": "password"
}
```

Login response:

```json
{
  "user": {
    "id": 1,
    "username": "research_user",
    "email": "research_user@example.com",
    "role": "viewer",
    "profile_picture": null
  },
  "token": "auth-token"
}
```

### Materials

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/materials` | Viewer | Search or list active materials. |
| `POST` | `/materials` | Staff | Create a material record. |
| `GET` | `/materials/{id}` | Viewer | View material details. |
| `PATCH` | `/materials/{id}` | Staff | Update material metadata. |
| `POST` | `/materials/{id}/archive` | Admin | Archive a material record without deleting it. |
| `POST` | `/materials/{id}/restore` | Admin | Restore an archived material when appropriate. |

### Locations

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/locations` | Viewer | List storage locations. |
| `POST` | `/locations` | Staff | Create a storage location. |
| `GET` | `/locations/{id}` | Viewer | View location details. |
| `PATCH` | `/locations/{id}` | Staff | Update location metadata without introducing a hierarchy cycle. |

### Inventory Operations

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `POST` | `/materials/{id}/adjust-quantity` | Admin | Adjust material quantity with a reason. |
| `POST` | `/materials/{id}/check-in` | Admin | Add received or returned quantity. |
| `POST` | `/materials/{id}/check-out` | Admin | Remove quantity for use, shipment, or disposal. |
| `POST` | `/materials/{id}/move` | Admin | Move material to a new location. |

### Orders

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/orders` | Viewer | List own requests; admins list all requests. |
| `POST` | `/orders` | Viewer | Validate unreserved stock and submit without reserving inventory. |
| `GET` | `/orders/{id}` | Viewer | View an owned request; admins may view all. |
| `POST` | `/orders/{id}/approve` | Admin | Validate unreserved stock, approve, and reserve inventory atomically. |
| `POST` | `/orders/{id}/reject` | Admin | Reject a request. |
| `POST` | `/orders/{id}/fulfill` | Admin | Revalidate the reservation and reduce inventory atomically. |
| `POST` | `/orders/{id}/cancel` | Viewer | Cancel an owned submitted or approved request. |

### Audit

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/audit-logs` | Admin | Review inventory and admin operation history. |

There are currently no `/qc-flags`, `/qc/run`, or `/shipments` endpoints. QC
flags, QC execution, and shipment records are planned features described in
[`docs/qc-and-shipments-plan.md`](docs/qc-and-shipments-plan.md).

### Pagination

`GET /materials`, `GET /materials/search`, `GET /orders`, `GET /locations`, and
`GET /audit-logs` accept `page` (minimum 1) and `size` (1–100, default 25). They
return `items`, `page`, `size`, `total`, and `pages`.

## Current Data Model

### User

Stores account and permission information.

Fields:

- `id`
- `username`
- `email`
- `password_hash`
- `role`
- `profile_picture`
- `created_at`

### Material

Stores mixed lab material metadata and quantity state.

Fields (including the computed response field noted below):

- `id`
- `material_code`
- `material_name`
- `material_type`
- `description`
- `source`
- `quantity_available`
- `quantity_reserved`
- `unit`
- `minimum_quantity`
- `availability_status` (computed response field; not stored)
- `qc_status`
- `storage_condition`
- `location_id`
- `is_archived`
- `archived_at`
- `archived_by_user_id`
- `archive_reason`
- `created_at`
- `updated_at`

### Location

Stores physical storage hierarchy.

Fields:

- `id`
- `name`
- `location_type`
- `parent_location_id`
- `temperature_zone`
- `description`
- `created_at`
- `updated_at`

Example hierarchy:

```text
Building -> Room -> Freezer -> Rack -> Box -> Position
```

### Order

Stores request and fulfillment information.

Fields:

- `id`
- `requested_by_user_id`
- `material_id`
- `requested_quantity`
- `reserved_quantity`
- `status`
- `request_notes`
- `reviewed_by_user_id`
- `reviewed_at`
- `outcome_notes`
- `is_archived`
- `archived_at`
- `archived_by_user_id`
- `archive_reason`
- `created_at`
- `updated_at`

Order statuses:

- `submitted`
- `approved`
- `rejected`
- `fulfilled`
- `canceled`

### Inventory Audit

Stores a durable log of important inventory operations.

Fields:

- `id`
- `user_id`
- `material_id`
- `operation_type`
- `before_value`
- `after_value`
- `reason`
- `created_at`

The proposed QC, shipment, and cross-domain audit-event models are intentionally
kept out of the current schema; they are evaluated in the planning document.

## Delivered Workflow

The current version implements this complete workflow:

1. Staff or admin creates storage locations and material records.
2. A viewer, staff user, or admin searches and views active materials.
3. A viewer, staff user, or admin submits a quantity-based material request.
4. Admin approves the request, which reserves inventory.
5. Admin fulfills the request, which reduces available inventory.
6. Admin can archive material records instead of deleting them.
7. Inventory changes create audit logs, including order reservation, fulfillment,
   and reservation release, with before/after inventory snapshots committed in the
   same transaction as the order transition.

## Delivery Status and Roadmap

### Delivered: Backend Foundation

- FastAPI project structure and MySQL connection.
- SQLAlchemy database access with schema changes owned by Alembic migrations.
- Authentication and role-based access control.

### Delivered: Materials and Locations

- Material create/read/update, detail, search, and filtering.
- Material archive and restore behavior.
- Location create/read/update with hierarchy cycle protection.

### Delivered: Quantity-Based Inventory

- Quantity adjustment, check-in, and check-out operations.
- Material movement between locations.
- Inventory audit logging and quantity business-rule tests.

### Delivered: Orders

- Order submission, admin approval/rejection, and fulfillment.
- Atomic reservation creation and release on eligible cancellation.
- End-to-end order inventory audit coverage through the audit API and reports.

### Planned: QC and Shipments

- Confirm the inventory/order readiness gates.
- Add a general append-only audit-event foundation.
- Evaluate QC flags, manual resolution, and versioned QC execution.
- Evaluate shipment records and their allowed state transitions.
- Add migrations, APIs, frontend guidance, and end-to-end audit tests only after
  the current workflows meet the gate.

The sequencing, role proposal, state machines, data models, and audit-chain
requirements are in [`docs/qc-and-shipments-plan.md`](docs/qc-and-shipments-plan.md).

## Follow-up Decisions

- What QC rules should be automated first?
- Should material `qc_status` be derived from open QC flags or remain a separate
  manual classification?
- Are there compliance, privacy, or access logging requirements for this lab data?
- Will a later shipment increment require split shipments or carrier integration?

## Current Status

The repository contains the working FastAPI and React implementation for users,
materials, locations, inventory, orders, reports, and inventory audits. Database
changes are versioned through Alembic and operational behavior is covered by the
backend and frontend test suites. QC flags, QC runs, and shipment records remain
planned.

- `GET /health` confirms the API is running.
- `/users/register`, `/users/login`, `/users/logout`, and `/users/me` provide the
  active authentication and account paths.

See `docs/development.md` for local setup, migration, test, and run commands.
