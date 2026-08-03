import os
import shutil
import logging
import threading
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

logger = logging.getLogger("sentinel.database")

_connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
_pool_args = {}
if "sqlite" not in settings.database_url:
    _pool_args = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    **_pool_args,
)

if "sqlite" in settings.database_url:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def backup_wal():
    """Copy the WAL file to a backup location whenever the DB is opened."""
    db_path = settings.database_url.replace("sqlite:///", "")
    if not db_path:
        return
    db_file = Path(db_path)
    if not db_file.exists():
        return
    backup_dir = db_file.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    wal_path = db_file.with_suffix(".db-wal")
    if wal_path.exists():
        try:
            shutil.copy2(wal_path, backup_dir / f"sentinel_wal_backup_{threading.get_ident()}.wal")
            logger.debug("WAL backup completed")
        except Exception as e:
            logger.warning(f"WAL backup failed: {e}")
    try:
        backup_path = backup_dir / f"sentinel_db_backup_{threading.get_ident()}.db"
        shutil.copy2(db_file, backup_path)
        logger.debug(f"DB backup to {backup_path}")
    except Exception as e:
        logger.warning(f"DB backup failed: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
