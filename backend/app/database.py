from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


_kwargs = {"connect_args": {"check_same_thread": False}} if settings.is_sqlite else {"pool_pre_ping": True}
engine = create_engine(settings.database_url, **_kwargs)

if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the pgvector extension (PostgreSQL) and any missing tables. Alembic is the managed path."""
    from . import models  # noqa: F401  (register tables)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
