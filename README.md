# Lab Storage Management API

FastAPI backend for managing mixed research lab materials, storage locations, quantity-based inventory, material requests, QC status, and audit-safe inventory operations.

This repository is currently in the planning stage. The README serves as the working product and architecture brief for the first implementation.

## Product Vision

Research labs often track materials across freezers, shelves, boxes, spreadsheets, shipment records, and manual request channels. This project centralizes those workflows into one backend API that supports:

- Searching and reviewing lab material records.
- Managing quantity-based inventory for mixed material types.
- Requesting materials from available stock.
- Approving, rejecting, and fulfilling requests.
- Tracking QC status and data quality issues.
- Preserving audit history for sensitive inventory operations.
- Restricting actions by user role.

## Repository Scope

This repo owns the backend API only.

- Backend: FastAPI application.
- Database: MySQL.
- API style: REST.
- Frontend: expected to be implemented separately by another project or collaborator.

The API should be designed so a React frontend can consume it later through documented endpoints and OpenAPI docs.

## Intended Users

| Role | Permission Level | Primary Needs |
| --- | --- | --- |
| Vendor | Viewer | View approved dashboard and inventory details. |
| Research Team | User / Buyer | Search materials, review availability, and submit material requests. |
| Data Management Team | Admin | Manage inventory, fulfill requests, update QC, audit activity, and clean inconsistent records. |

Permission priority:

```text
Viewer < User < Admin
```

## Material Scope

The system should support mixed lab materials through one shared material model, with material-specific details captured through fields such as `material_type`, `unit`, `storage_condition`, and notes.

Example material types:

- Biological specimens.
- Chemicals and reagents.
- Lab consumables.
- Controls or reference materials.
- Other research materials tracked by quantity.

The MVP should avoid building separate tables for every material type unless a later requirement makes that necessary.

## Core Workflows

### Inventory Discovery

Users can search for stored materials by identifiers, material type, storage location, QC status, availability, and other indexed fields.

Expected capabilities:

- Inventory dashboard metrics.
- Searchable material list.
- Material detail endpoint.
- Quantity and availability visibility.
- Read-only views for viewer-level users.

### Material Requests

Research users can request a quantity of available material. Admin users review, approve, reject, and fulfill those requests.

Expected capabilities:

- Submit a material request with requested quantity and notes.
- Prevent requests for archived materials.
- Prevent requests above available quantity.
- Track request status.
- Reserve inventory after approval.
- Reduce inventory after fulfillment.
- Link fulfilled requests to shipment records when needed.

### Inventory Operations

Admin users can maintain inventory state over time.

Expected capabilities:

- Create material records.
- Update material metadata.
- Adjust available quantity.
- Move materials between storage locations.
- Check materials in or out.
- Archive materials instead of permanently deleting them.
- Record sensitive changes in audit logs.

### QC and Data Maintenance

Admin users can review QC status, run consistency checks, and clean records.

Expected capabilities:

- View QC flags.
- Trigger QC checks.
- Update QC status.
- Identify missing or inconsistent fields.
- Preserve audit history for manual corrections.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3, FastAPI |
| Database | MySQL |
| ORM / Database Layer | SQLAlchemy |
| Migrations | Alembic |
| Validation | Pydantic |
| Authentication | Token-based authentication |
| API Documentation | FastAPI OpenAPI docs |
| Testing | Pytest |

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
SQLAlchemy models
        |
        v
MySQL database
```

Recommended backend modules:

- `auth`: registration, login, logout, token validation, role checks.
- `users`: account and permission management.
- `materials`: material CRUD, archive lifecycle, material detail records.
- `locations`: storage hierarchy and location metadata.
- `inventory`: quantity adjustments, reservation, check-in, check-out, movement, availability.
- `orders`: request submission, review, approval, rejection, fulfillment, and outcomes.
- `shipments`: shipment tracking for fulfilled requests.
- `qc`: QC flags, QC checks, and data consistency maintenance.
- `audit`: immutable operation logs.

## Business Rules

The MVP should implement these rules before adding advanced features:

- A user cannot request an archived material.
- A user cannot request more than the available quantity.
- Approving a request reserves the requested quantity.
- Fulfilling a request subtracts the reserved quantity from inventory.
- Rejecting or canceling a request releases any reserved quantity.
- Archived materials remain in the database but are hidden from normal active inventory searches.
- Admin inventory changes create audit log records.
- Viewer users cannot create, update, archive, approve, or fulfill records.
- User-level accounts can search materials and submit requests, but cannot directly change inventory.

## Planned API

### Authentication

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a new user account. |
| `POST` | `/auth/login` | Authenticate a user and return a token. |
| `POST` | `/auth/logout` | Invalidate or retire a user session token. |

Login request:

```json
{
  "userId": "research_user",
  "password": "password"
}
```

Login response:

```json
{
  "userId": "research_user",
  "token": "auth-token"
}
```

### Materials

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/materials` | Viewer | Search or list active materials. |
| `POST` | `/materials` | Admin | Create a material record. |
| `GET` | `/materials/{id}` | Viewer | View material details. |
| `PATCH` | `/materials/{id}` | Admin | Update material metadata. |
| `POST` | `/materials/{id}/archive` | Admin | Archive a material record without deleting it. |
| `POST` | `/materials/{id}/restore` | Admin | Restore an archived material when appropriate. |

### Locations

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/locations` | Viewer | List storage locations. |
| `POST` | `/locations` | Admin | Create a storage location. |
| `GET` | `/locations/{id}` | Viewer | View location details. |
| `PATCH` | `/locations/{id}` | Admin | Update location metadata. |

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
| `GET` | `/orders` | User | List visible requests. |
| `POST` | `/orders` | User | Submit a material request. |
| `GET` | `/orders/{id}` | User | View request details. |
| `POST` | `/orders/{id}/approve` | Admin | Approve a request and reserve inventory. |
| `POST` | `/orders/{id}/reject` | Admin | Reject a request. |
| `POST` | `/orders/{id}/fulfill` | Admin | Fulfill an approved request and reduce inventory. |
| `POST` | `/orders/{id}/cancel` | User | Cancel a request when allowed. |

### QC and Audit

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/qc-flags` | Admin | List QC flags. |
| `POST` | `/qc/run` | Admin | Run QC or data consistency checks. |
| `PATCH` | `/materials/{id}/qc-status` | Admin | Update material QC status. |
| `GET` | `/audit-logs` | Admin | Review inventory and admin operation history. |

## Initial Data Model

### User

Stores account and permission information.

Suggested fields:

- `id`
- `user_id`
- `name`
- `email`
- `password_hash`
- `role`
- `created_at`
- `updated_at`

### Material

Stores mixed lab material metadata and quantity state.

Suggested fields:

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
- `availability_status`
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

Suggested fields:

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

Suggested fields:

- `id`
- `requested_by_user_id`
- `material_id`
- `requested_quantity`
- `reserved_quantity`
- `unit`
- `request_status`
- `request_notes`
- `reviewed_by_user_id`
- `submitted_at`
- `approved_at`
- `fulfilled_at`
- `canceled_at`
- `outcome_notes`

Suggested request statuses:

- `submitted`
- `approved`
- `rejected`
- `fulfilled`
- `canceled`

### Shipment

Stores transfer and tracking information for fulfilled requests.

Suggested fields:

- `id`
- `order_id`
- `material_id`
- `carrier`
- `tracking_number`
- `shipped_at`
- `received_at`
- `shipment_status`

### QC Flag

Stores QC or data quality issues related to a material.

Suggested fields:

- `id`
- `material_id`
- `flag_type`
- `severity`
- `description`
- `status`
- `created_by_user_id`
- `resolved_by_user_id`
- `created_at`
- `resolved_at`

### Inventory Audit

Stores a durable log of important inventory operations.

Suggested fields:

- `id`
- `user_id`
- `material_id`
- `operation_type`
- `before_value`
- `after_value`
- `reason`
- `created_at`

## MVP Scope

The first useful version should focus on one complete backend workflow:

1. Admin creates storage locations.
2. Admin creates mixed material records with quantity and unit.
3. Viewer or user searches and views active material records.
4. User submits a quantity-based material request.
5. Admin approves the request, which reserves inventory.
6. Admin fulfills the request, which reduces available inventory.
7. Admin can archive material records instead of deleting them.
8. Admin inventory changes create audit logs.

## Development Roadmap

### Phase 1: Backend Foundation

- Create FastAPI project structure.
- Configure MySQL connection.
- Add SQLAlchemy models.
- Add Alembic migrations.
- Implement authentication and role-based access control.
- Add seed data for local development.

### Phase 2: Materials and Locations

- Implement material CRUD.
- Implement archive and restore behavior.
- Implement location CRUD.
- Implement material search and filtering.
- Add material detail endpoint.

### Phase 3: Quantity-Based Inventory

- Implement quantity adjustment.
- Implement check-in and check-out operations.
- Implement material movement between locations.
- Add inventory audit logging.
- Add tests for quantity business rules.

### Phase 4: Orders

- Implement order submission.
- Implement admin approval and rejection.
- Implement reservation behavior.
- Implement fulfillment behavior.
- Release reserved quantity on cancellation or rejection.

### Phase 5: QC and Operational Polish

- Implement QC flag listing.
- Add manual QC status updates.
- Add automated consistency checks.
- Add API error handling.
- Expand test coverage.
- Prepare deployment configuration.

## Open Questions

- What exact material types should the first version support?
- What fields must be searchable from day one?
- What units should be supported initially, such as `tube`, `mL`, `mg`, `box`, or `each`?
- Should low-stock alerts be part of the MVP or a later feature?
- What QC rules should be automated first?
- Are there compliance, privacy, or access logging requirements for this lab data?
- Does shipment tracking need to integrate with external carrier APIs, or is manual tracking enough for MVP?

## Current Status

Early implementation. The repository now contains a minimal FastAPI starter framework for the
first learning milestone:

- `GET /health` confirms the API is running.
- `/test-table` shows simple MySQL CRUD against the existing `test_table`.
- `/users/register`, `/users/login`, and `/users/logout` provide the first user module skeleton.

See `docs/development.md` for local setup, table SQL, and run commands.
