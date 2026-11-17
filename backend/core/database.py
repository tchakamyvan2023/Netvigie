"""
NETVIGIE — Connexion PostgreSQL via SQLAlchemy 2.0
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from backend.core.config import settings
from backend.models.base import Base

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.app_debug,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : fournit une session par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager pour usage hors FastAPI (scripts, agents)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Crée toutes les tables."""
    # Import des modèles pour les enregistrer dans Base.metadata
    from backend.models import (  # noqa: F401
        user, agent_wazuh, agent_netvigie, machine,
        event, alert, incident, audit_log,
    )
    Base.metadata.create_all(bind=engine)


def test_connection() -> bool:
    """Test rapide de la connexion."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        return False