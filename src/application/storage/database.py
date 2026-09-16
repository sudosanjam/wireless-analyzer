"""
SQLite connection manager with WAL mode and transaction safety.
"""

from pathlib import Path
import sqlite3
import threading
from typing import Generator
from contextlib import contextmanager
from application.storage.schema import SCHEMA_SQL
from application.utils.logging import get_logger

logger = get_logger("database")


class DatabaseManager:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: str | Path = "data/app.db") -> None:
        self.db_path = Path(db_path)
        self._local = threading.local()
        self.initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=20.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            # Execute PRAGMA configurations
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.connection = conn
        return self._local.connection

    def initialize_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = self._get_connection()
            with conn:
                conn.executescript(SCHEMA_SQL)
            logger.info("Database initialized successfully at %s", self.db_path)
        except Exception as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for atomic transactions with automatic rollback on error."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        """Close current thread connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None
