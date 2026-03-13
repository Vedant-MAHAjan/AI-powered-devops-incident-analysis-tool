"""Database setup and session management."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base


_engine = None
_session_factory = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Ensure the data directory exists
        db_path = settings.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db():
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get a database session. Use as a context manager or dependency."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
