# Development Guide

This project is intentionally small at the beginning. The first goal is to learn how a FastAPI
project is organized, how routes call service functions, and how the service layer talks to MySQL.

## 1. Install Dependencies

```bash
uv sync --extra dev
```

## 2. Start MySQL

```bash
docker compose -f docker/docker-compose.yaml up -d
```

The default local database settings are:

```text
Database: lab_storage_db
User: lab_user
Password: lab_password
Port: 3306
```

## 3. Create Learning Tables

Create the simple table used by the example CRUD module:

```sql
CREATE TABLE IF NOT EXISTS test_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);
```

Create the first user table for the user module:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 4. Run the API

```bash
uv run uvicorn src.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

## 5. Try the First Endpoints

Health check:

```http
GET /health
```

Example CRUD table:

```http
GET /test-table
POST /test-table
PATCH /test-table/{item_id}
DELETE /test-table/{item_id}
```

User module:

```http
POST /users/register
POST /users/login
POST /users/logout
```

## Project Shape

```text
src/
  main.py              # Creates the FastAPI app and registers routers.
  core/config.py       # Reads environment configuration.
  db/connection.py     # Creates the SQLAlchemy database session.
  health/router.py     # Minimal API health check.
  test_table/          # Example CRUD module for the existing test_table.
  user/                # First real business module: register, login, logout.
  utils/security.py    # Small password hashing and token helpers.
```

When adding a new feature, follow the same pattern:

1. Define request and response models in `schemas.py`.
2. Put database logic in `service.py`.
3. Put FastAPI routes in `router.py`.
4. Register the router in `src/main.py`.
