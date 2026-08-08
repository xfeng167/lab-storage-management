# Lab Storage Management Frontend

This directory contains the standalone React frontend for Lab Storage Management. It is a responsive, role-aware operations workspace built against the FastAPI endpoints currently available in this repository. Frontend changes remain isolated to `front-end/`.

## Delivered Capabilities

- Authentication: registration, login, persistent token restoration, invalid-session recovery, and logout.
- Workspace dashboard: active stock, quantity, low-stock, request, and recent-activity signals appropriate to the signed-in role.
- Inventory catalogue: material search and filters, direct material details, request submission, staff material creation and editing, plus administrator quantity adjustment, check-in, check-out, movement, archive, and restore workflows.
- Storage locations: staff can create and update locations; the interface shows hierarchy, temperature zones, and location details.
- Material requests: users can submit and track requests; administrators can approve, reject, fulfill, or cancel requests with outcome notes.
- Reporting: staff and administrators can view low-stock materials, submitted requests, recent inventory activity, and materials grouped by storage location.
- Administration: administrators can review inventory audit logs with filters and browse the user directory.
- Quality controls: typed API client, role-protected routes, responsive layouts, accessible labels/dialogs, empty/loading/error states, automated tests, linting, and production builds.

The non-product `/test-table` learning endpoint is intentionally not exposed in the operational UI.

## Role Matrix

| Capability | Viewer | Staff | Admin |
| --- | :---: | :---: | :---: |
| Browse materials and create requests | Yes | Yes | Yes |
| View own requests | Yes | Yes | Yes |
| View all requests and review their lifecycle | No | No | Yes |
| Create or edit materials and locations | No | Yes | Yes |
| Inventory quantity, movement, and archive operations | No | No | Yes |
| Operational reports | No | Yes | Yes |
| Audit log and user directory | No | No | Yes |

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
docker compose -f docker/docker-compose.yaml up -d
uv run uvicorn src.main:app --reload
```

Create the API tables described in `docs/development.md` before using the frontend. The application requires `users`, `token_table`, `locations`, `materials`, `inventory_audit_logs`, and `orders`.

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

The client stores the backend token in browser `localStorage` and sends it with `Authorization: Bearer <token>`. It validates saved sessions through `/users/me` at startup and clears the local session after any API 401 response. The current backend token lifetime is one hour.

## API Coverage

The operational UI integrates the available product API groups:

- `/users`: account registration, authentication, session, and administrator directory.
- `/materials`: catalogue, search, detail, material metadata, archive lifecycle, and inventory operations.
- `/locations`: storage location list, detail, creation, and update.
- `/orders`: request creation, list/detail, approval, rejection, fulfillment, and cancellation.
- `/reports`: low-stock, pending orders, activity, and location summaries.
- `/audit-logs`: administrator audit-log review and filtering.
- `/health`: backend readiness is available to deployment and monitoring infrastructure; it is not a user-facing operational screen.

## Backend Collaboration Notes

The current backend has no profile editing, password reset, role management, pagination, file attachment, or export endpoints. The frontend does not invent client-only mutations for these capabilities. Add the corresponding API contract before extending the interface.

The backend is responsible for enforcing all authorization and inventory business rules. The frontend reflects role capabilities and performs user-friendly validation, but API authorization and state transitions remain the source of truth.
