# Frontend Directory Guidance

This directory contains the standalone frontend application, including React source code, Vite and Tailwind configuration, automated tests, and frontend documentation.

## Agent Scope

- Agents responsible for backend implementation, backend analysis, database work, FastAPI work, or backend testing do not need to read, search, or modify this directory. Focus on the backend source and documentation at the repository root instead.
- Agents responsible for frontend implementation, frontend review, frontend testing, or UI/UX work should use this directory as their working scope.

## Frontend Constraints

- Keep frontend changes within `front-end/` unless the user explicitly authorizes a broader change.
- Do not modify backend source code, backend configuration, or root-level project files as part of frontend work.
- Use English for source code, code comments, and user-facing interface copy.
