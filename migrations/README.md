# Database migrations

Alembic is the only source of database schema definitions. Apply every pending
migration before starting the API:

```bash
uv run alembic upgrade head
```
Create future revisions with `uv run alembic revision -m "description"`. Do not
add schema-changing SQL to application startup or duplicate table definitions in
test fixtures.
