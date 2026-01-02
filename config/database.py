"""Database configuration and session management."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, Any, None]:
    """Dependency that provides a database session.

    Yields a SQLAlchemy session and ensures proper cleanup after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
