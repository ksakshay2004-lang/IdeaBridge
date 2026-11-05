"""initial schema (baseline)

The baseline creates the pgvector extension and every table from the current SQLAlchemy metadata.
Subsequent schema changes should be generated with:  alembic revision --autogenerate -m "describe change"

Revision ID: 0001
Revises:
"""
from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind)
    if bind.dialect.name == "postgresql":
        # Approximate-nearest-neighbour indexes for cosine distance (optional but recommended at scale).
        op.execute("CREATE INDEX IF NOT EXISTS ix_ideas_embedding_cos ON ideas USING hnsw (embedding vector_cosine_ops)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_refs_embedding_cos ON reference_projects USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
