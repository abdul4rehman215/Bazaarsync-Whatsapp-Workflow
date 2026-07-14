"""
Database engine + session management (SQLAlchemy 2.0 style).

Defaults to SQLite for a zero-config local run. Swap DATABASE_URL to a
Postgres DSN in .env for production - no code changes required.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Fine for SQLite/dev; use Alembic migrations in prod."""
    from app import models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)
