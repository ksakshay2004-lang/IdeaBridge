# Database

* Engine: PostgreSQL 16 with the **pgvector** extension (image `pgvector/pgvector:pg16`).
* `init.sql` enables the extension on first container start.
* Schema management:
  * `cd backend && alembic upgrade head` (recommended for real deployments), or
  * automatic `create_all` at backend start-up when `AUTO_CREATE_TABLES=true` (default, convenient for development).
* Sample data: set `SEED_DEMO_DATA=true` (only seeds an empty database). Demo password: `Demo@12345`.
* The ER diagram is in `docs/ARCHITECTURE.md`.
* Vector columns are `vector(384)`; `EMBEDDING_DIM` must match. Changing the embedding model requires
  `POST /api/admin/reindex` (or the "Reindex" button on the admin dashboard).
