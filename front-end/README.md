# Lab Storage Management Frontend

This directory contains the standalone React frontend for Lab Storage Management. It is a responsive, role-aware operations workspace built against the FastAPI endpoints currently available in this repository. Frontend changes remain isolated to `front-end/`.

## Delivered Capabilities

- Authentication: registration, login, persistent token restoration, invalid-session recovery, logout, and current-password-verified password changes.
- Workspace dashboard: active stock, quantity, low-stock, request, and recent-activity signals appropriate to the signed-in role.
- Inventory catalogue: material search and filters, direct material details, request submission, staff material creation and editing, plus administrator quantity adjustment, check-in, check-out, movement, archive, and restore workflows.
- Storage locations: staff can create and update locations; the interface shows hierarchy, temperature zones, and location details.
- Material requests: every authenticated role can submit, track, and cancel its own requests; administrators can review all requests.
- Reporting: staff and administrators can view low-stock materials, submitted requests, recent inventory activity, and materials grouped by storage location.
- Administration: administrators can review inventory/order audit logs and assign roles in the user directory.
- Quality controls: typed API client, role-protected routes, responsive layouts, accessible labels/dialogs, empty/loading/error states, automated tests, linting, and production builds.

The production API does not register the non-product `/test-table` learning endpoint.

## Role Matrix

| Capability | Viewer | Staff | Admin |
| --- | :---: | :---: | :---: |
| Browse materials and create requests | Yes | Yes | Yes |
| View, cancel, and archive own eligible requests | Yes | Yes | Yes |
| View all requests and review their lifecycle | No | No | Yes |
| Create or edit materials and locations | No | Yes | Yes |
| Inventory quantity, movement, and archive operations | No | No | Yes |
| Operational reports | No | Yes | Yes |
| Audit log and user directory | No | No | Yes |

Material archive is blocked while an approved order or reservation exists. The
request must be fulfilled or canceled first. Archive and restore are audited, and
restore clears the material's archive timestamp, actor, and reason. Availability is
computed from unreserved stock on every response rather than trusted from a stored
status column.
Terminal orders require a reason to archive, cannot be restored, and keep their
original archive metadata and audit record if a duplicate archive is attempted.

## Run Locally

Prerequisite: Node.js 16.18 or later. The project uses React 18 and Vite 4 to remain compatible with the current repository environment.

```bash
cd front-end
npm install
npm run dev
```

The development server uses `http://127.0.0.1:5173` by default. If that port is already in use, Vite prints the selected alternative port.

Start the backend and local MySQL from the repository root in separate terminals:

```bash
docker compose -f docker/docker-compose.dev.yaml up -d
export DATABASE_URL='mysql+pymysql://lab_user:lab_password@localhost:3306/lab_storage_db'
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

Alembic migrations create and update the API schema. Application startup does not
perform database DDL.

## Commands

```bash
npm run dev        # Start the frontend development server
npm run lint       # Run ESLint with warnings treated as failures
npm run test       # Run Vitest tests
npm run build      # Type-check and generate a production build
```

## Environment and API Access

Copy `.env.example` to `.env.local` and configure the API base URL:

```env
VITE_API_BASE_URL=/api
```

For local development, keep the `/api` value. Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, so `/api/materials` reaches the backend route `/materials` without a browser CORS request.

For a production deployment, set `VITE_API_BASE_URL` to the full backend API base URL, for example `https://api.example.com`. The backend must explicitly allow the frontend origin through CORS before using a separate domain.

The client stores the backend token in browser `localStorage` and sends it with `Authorization: Bearer <token>`. It validates saved sessions through `/users/me` at startup and clears the local session after any API 401 response. Password changes revoke all tokens and return the user to sign-in. Token lifetime is configured by the backend (`TOKEN_TTL_MINUTES`, 60 by default).

Backend failures use `{ "error": { "code", "message", "details" } }`. The client
exposes these as `ApiError.status`, `ApiError.code`, `ApiError.message`, and
optional `ApiError.details`; UI copy displays the message while conditional
behavior should use the stable code.

## API Coverage

The operational UI integrates the available product API groups:

- `/users`: account registration, authentication, session, and administrator directory.
- `/materials`: catalogue, search, detail, material metadata, archive lifecycle, and inventory operations.
- `/locations`: storage location list, detail, creation, and update.
- `/orders`: request creation, list/detail, approval, rejection, fulfillment, and cancellation.
- `/reports`: low-stock, pending orders, activity, and location summaries.
- `/audit-logs`: administrator audit-log review and filtering.
- `/health`: process liveness; `/health/ready`: database and migration readiness.

## Backend Collaboration Notes

The current backend has no self-service forgotten-password reset,
file attachment, or export endpoints. Materials, material search, orders,
locations, audit logs, and users expose bounded `page`/`size` pagination with
totals. Primary screens show page controls; selectors and summaries retrieve
every page instead of treating the first 100 rows as complete.

The backend is responsible for enforcing all authorization and inventory business rules. The frontend reflects role capabilities and performs user-friendly validation, but API authorization and state transitions remain the source of truth.
