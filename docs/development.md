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
Server: mysql
http://localhost:8080/?server=mysql&username=lab_user&db=lab_storage_db
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
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create the token table used by login/logout:

```sql
CREATE TABLE IF NOT EXISTS token_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(255) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

Create the first materials table:

The application validates `location_id` against the `locations` table when a material is created or updated.

```sql
CREATE TABLE IF NOT EXISTS materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_code VARCHAR(80) NOT NULL UNIQUE,
    material_name VARCHAR(255) NOT NULL,
    material_type VARCHAR(80) NOT NULL,
    description TEXT,
    source VARCHAR(255),
    quantity_available INT NOT NULL DEFAULT 0,
    quantity_reserved INT NOT NULL DEFAULT 0,
    unit VARCHAR(40) NOT NULL,
    minimum_quantity INT NOT NULL DEFAULT 0,
    availability_status VARCHAR(40) NOT NULL DEFAULT 'available',
    qc_status VARCHAR(40) NOT NULL DEFAULT 'pending',
    storage_condition VARCHAR(120),
    location_id INT,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMP NULL,
    archived_by_user_id INT NULL,
    archive_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

Create the first locations table:

```sql
CREATE TABLE IF NOT EXISTS locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    location_type VARCHAR(80) NOT NULL,
    parent_location_id INT NULL,
    temperature_zone VARCHAR(80),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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
```

Location module:

```http
GET /locations
GET /locations/{location_id}
POST /locations
PATCH /locations/{location_id}
```

Material search supports these optional query parameters:

```text
material_type
qc_status
availability_status
location_id
include_archived
```

Protected endpoints use the authorization header:

```http
Authorization: Bearer <token>
```

## Project Shape

```text
src/
  main.py              # Creates the FastAPI app and registers routers.
  auth/                # Token validation and reusable auth dependencies.
  core/config.py       # Reads environment configuration.
  db/connection.py     # Creates the SQLAlchemy database session.
  health/router.py     # Minimal API health check.
  location/            # Storage location CRUD endpoints.
  material/            # Material CRUD, search, archive, and restore endpoints.
  test_table/          # Example CRUD module for the existing test_table.
  user/                # User registration, login, logout, and profile endpoints.
  utils/security.py    # Password hashing and token helper functions.
  utils/constant.py    # Shared role constants.
```

When adding a new feature, follow the same pattern:

1. Define request and response models in `schemas.py`.
2. Put database logic in `service.py`.
3. Put FastAPI routes in `router.py`.
4. Register the router in `src/main.py`.
