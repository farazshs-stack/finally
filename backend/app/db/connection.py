"""SQLite connection management for FinAlly.

DB path resolution order:
  1. DATABASE_PATH environment variable (absolute or relative to project root)
  2. Default: 'db/finally.db' relative to the project root (two levels up from this file)

Thread safety: each call to get_connection() returns a fresh connection bound to the
calling thread's context (check_same_thread=False is safe because we never share a
connection object across threads — we open per-call and close via context manager).

Usage:
    from app.db.connection import get_connection, init_db

    init_db()          # lazy, idempotent — call once at app startup
    with get_connection() as conn:
        rows = conn.execute("SELECT ...").fetchall()
"""

import os
import sqlite3
from pathlib import Path


def _resolve_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    env_path = os.environ.get("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        # If relative, resolve from project root (parent of backend/)
        if not p.is_absolute():
            _project_root = Path(__file__).parent.parent.parent.parent
            p = _project_root / p
    else:
        # Default: <project_root>/db/finally.db
        _project_root = Path(__file__).parent.parent.parent.parent
        p = _project_root / "db" / "finally.db"
    return p.resolve()


def get_db_path() -> Path:
    """Return the resolved database file path (public helper)."""
    return _resolve_db_path()


def get_connection() -> sqlite3.Connection:
    """Open and return a new SQLite connection configured for FinAlly.

    The caller is responsible for closing the connection.  Prefer using it as a
    context manager so it auto-commits / rolls back and closes:

        with get_connection() as conn:
            conn.execute(...)   # auto-committed on __exit__

    Raises:
        OSError: if the parent directory cannot be created.
    """
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL for better concurrency under FastAPI's thread-pool
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
