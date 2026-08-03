# Lab Storage Management Frontend

This is the standalone frontend for Lab Storage Management. It currently implements authentication and account features only. All source code, dependencies, and build artifacts are contained within this directory; backend code is not modified.

## Current Progress

- Registration, login, persistent session restoration, and logout are implemented.
- A protected account overview displays the username, email address, role, account ID, and session guidance.
- An administrator-only user directory is implemented; it is available only when the backend returns the `admin` role.
- The responsive desktop and mobile interface includes form validation, loading and error states, and foundational accessibility semantics.
- Automated tests cover the API client, registration validation, session restoration, logout, route protection, and the administrator directory.

This phase does not include inventory, materials, locations, orders, profile editing, or password changes. The current backend does not expose the APIs required for those features.

## Run Locally

Prerequisite: Node.js 16.18 or later. This project uses Vite 4 and React 18 for compatibility with the current repository environment.

```bash
cd front-end
npm install
npm run dev
```

The development server runs at `http://127.0.0.1:5173` by default. Start the backend separately:

```bash
uv run uvicorn src.main:app --reload
```

The frontend development server proxies `/api/*` to `http://127.0.0.1:8000/*`. For example, a browser request to `/api/users/login` is forwarded to the backend endpoint `/users/login`.

## Commands

```bash
npm run dev        # Start the development server
npm run lint       # Run ESLint
npm run test       # Run Vitest tests
npm run build      # Type-check and create a production build
```

## Environment Variables and API Contract

Copy `.env.example` to `.env.local` and set the value for the target environment:

```env
VITE_API_BASE_URL=/api
```

Keep `/api` for local development to use the Vite proxy. In production, set the variable to the full backend API base URL, such as `https://api.example.com`; the backend must then configure CORS for the frontend origin.

The frontend currently depends on the following backend endpoints:

- `POST /users/register`
- `POST /users/login`
- `POST /users/logout`
- `GET /users/me`
- `GET /users` (administrator only)

The login token is saved in browser `localStorage` and sent using `Authorization: Bearer <token>`. The current backend implementation expires tokens after one hour. On application startup, the frontend validates the saved token through `/users/me`; a 401 response clears the local session and returns the user to sign-in.

## Backend Collaboration Notes

The current FastAPI project does not include CORS middleware. The Vite proxy handles this during development, but production deployment requires backend engineers to explicitly allow the frontend origin. Future support for profile editing, password resets, role management, or user pagination requires corresponding backend APIs before it can be added here.
