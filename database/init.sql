-- Runs once when the Postgres container is first created (docker-entrypoint-initdb.d).
-- Tables are created by the backend (init_db) or by `alembic upgrade head`.
CREATE EXTENSION IF NOT EXISTS vector;
