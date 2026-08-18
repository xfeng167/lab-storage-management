# QC and Shipment Module Plan

Status: planned; no routes, tables, or migrations in this document are currently
implemented.

## Implementation Gate

QC flags, QC execution, and shipment records may enter implementation only after
all of these conditions hold for the inventory and order workflows:

- A clean database and an upgraded existing database both reach the same Alembic
  head without application-startup DDL.
- Submission, approval, fulfillment, rejection, and cancellation tests pass,
  including insufficient-stock, concurrent approval, retry, and rollback cases.
- Approval, fulfillment, and approved-order cancellation each commit their order,
  inventory, and audit changes atomically and are visible through both
  `/audit-logs` and `/reports/recent-inventory-activity`.
- Availability is derived from unreserved stock on reads and searches; no stale
  stored status can influence results.
- The viewer/staff/admin policy, structured error contract, pagination limits,
  material archive policy, and location-cycle protection are stable and described
  by README and OpenAPI tests.
- There are no unresolved high-severity inventory consistency or order-transition
  defects.

If a gate regresses, QC/shipment implementation pauses until the underlying
workflow is fixed. Planning does not change current order or inventory behavior.

## Shared Audit Foundation

The current `inventory_audit_logs` table is intentionally material- and
inventory-specific. QC runs and shipments need a cross-domain, append-only audit
chain rather than encoded strings forced into that table.

Before either module, add a migration-managed `audit_events` table with:

- `id`, `event_type`, `entity_type`, and `entity_id`.
- Nullable indexed links for `material_id`, `order_id`, and the acting `user_id`.
- A `correlation_id` shared by one command and an optional `causation_event_id`.
- Structured before/after payloads, a reason, and an immutable `created_at`.

Events are written in the same transaction as each domain transition. Retries
must use an idempotency key or an equivalent uniqueness rule so they cannot create
duplicate transitions or events. The existing inventory audit API remains
compatible; a later general audit API can expose the cross-domain chain with
entity, event, actor, correlation, and time filters plus capped pagination.

## QC Evaluation

### Proposed records

`qc_runs` represents one versioned evaluation: status (`queued`, `running`,
`succeeded`, or `failed`), ruleset version, requester, start/finish times, counts,
and a failure summary. `qc_flags` represents a finding for one material: stable
rule code, severity, status (`open`, `resolved`, or `dismissed`), evidence,
run/creator, resolution actor/reason, and timestamps.

A rule-version/material/finding fingerprint should prevent duplicate open flags
when a run is retried. Historical flags are never overwritten by a new ruleset;
resolution is an explicit transition. Automated runs read a consistent inventory
snapshot and do not adjust stock or change order state.

### Proposed permissions and API shape

- Viewer: sees only the existing material `qc_status`; no flag or run access.
- Staff: reads flags and run results as operational reports.
- Admin: starts runs and resolves or dismisses flags with a required reason.

Candidate endpoints are `GET /qc-flags`, `GET /qc-flags/{id}`,
`POST /qc/runs`, `GET /qc/runs/{id}`, and explicit resolve/dismiss operations.
All list operations require capped pagination. These paths stay out of OpenAPI
until implemented.

### Audit chain

At minimum record `qc_run_requested`, `qc_run_started`, `qc_flag_opened`,
`qc_flag_resolved`, `qc_flag_dismissed`, `qc_run_succeeded`, and `qc_run_failed`.
A run and every flag it creates share a correlation ID and record the ruleset
version. Manual transitions include actor, reason, and before/after status.

The existing editable `materials.qc_status` needs a product decision before this
module starts: either derive it from unresolved flags or retain it as a separate
manual classification. Running both without an explicit precedence rule would
create contradictory QC state.

## Shipment Evaluation

### Proposed records and state machine

Start with exactly one shipment per fulfilled order (`UNIQUE order_id`) because a
current order has one material and one fulfilled quantity. Supporting split
shipments later requires shipment-line quantities and a separate reconciliation
design.

A shipment stores its order link, status, carrier/tracking data, recipient
snapshot, creator/updater, and created/ready/shipped/delivered/canceled times.
The initial allowed transitions are:

```text
draft -> ready -> shipped -> delivered
   |        |
   +------> canceled
```

A shipped record is not deleted or reset to canceled; delivery exceptions and
returns should be separate later events. Shipment creation and status changes do
not alter stock: fulfillment remains the only deduction point. Canceling a
shipment does not cancel the fulfilled order or restore inventory.

### Proposed permissions and API shape

- Viewer: reads shipment status only for an owned order.
- Staff: creates and updates shipment records for fulfilled orders.
- Admin: staff access plus exception/cancellation authority.

Candidate endpoints are `POST /orders/{id}/shipment`, `GET /shipments`,
`GET /shipments/{id}`, and explicit ready, dispatch, deliver, and cancel
operations. All list operations require capped pagination. Carrier integration is
out of scope for the first increment; tracking is manual.

### Audit chain

Record `shipment_created`, `shipment_ready`, `shipment_dispatched`,
`shipment_delivered`, and `shipment_canceled`, with actor, reason, before/after
status, order/material links, and one correlation ID for each command. Recipient
and tracking snapshots make later profile edits harmless to historical records.

QC must not silently become a fulfillment or dispatch blocker. The first shipment
increment should show the material QC snapshot as information only. A hard QC gate
requires a separately approved, versioned policy and new order-workflow tests.

## Proposed Sequence

1. Confirm and record that every implementation-gate item is green.
2. Add the general audit-event migration, service, API, pagination, and tests.
3. Resolve the `materials.qc_status` precedence decision.
4. Implement read-only QC flags, then manual resolution, then versioned execution.
5. Implement one-shipment-per-fulfilled-order records and explicit transitions.
6. Add end-to-end audit-chain, authorization, concurrency, retry, migration, and
   OpenAPI tests for each increment before exposing frontend controls.
