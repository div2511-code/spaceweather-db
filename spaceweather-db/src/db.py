"""Database connection helper. All modules use get_connection()."""

import os
import sqlite3
from contextlib import contextmanager


def _default_db_path() -> str:
    """Resolve at call time so tests/tools can override SWDB_PATH dynamically."""
    return os.environ.get("SWDB_PATH", "spaceweather.db")


@contextmanager
def get_connection(path: str | None = None):
    """Context-managed SQLite connection with foreign keys on."""
    conn = sqlite3.connect(path or _default_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
