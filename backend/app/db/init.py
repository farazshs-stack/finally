"""Lazy, idempotent database initialisation.

Call ``init_db()`` once at application startup (e.g. in a FastAPI lifespan
handler).  It is safe to call multiple times — every operation is guarded by
IF NOT EXISTS or existence checks.

What it does:
  1. Creates the parent directory for the DB file if it doesn't exist.
  2. Runs all CREATE TABLE IF NOT EXISTS statements.
  3. Seeds the default user profile if no row exists for id='default'.
  4. Seeds the 10 default watchlist tickers if the watchlist is empty for
     the 'default' user.
"""

import sqlite3

from .connection import get_connection
from .schema import ALL_DDL, DEFAULT_CASH_BALANCE, DEFAULT_TICKERS, DEFAULT_USER_ID
from .utils import new_uuid, utc_now


def init_db() -> None:
    """Create tables and seed defaults.  Idempotent — safe on every startup."""
    conn = get_connection()
    try:
        _create_schema(conn)
        _seed_defaults(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
    """Execute all DDL statements."""
    for ddl in ALL_DDL:
        conn.execute(ddl)


def _seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert default user profile and watchlist if they don't exist."""
    _seed_user_profile(conn)
    _seed_watchlist(conn)


def _seed_user_profile(conn: sqlite3.Connection) -> None:
    """Insert the default user profile row if absent."""
    row = conn.execute(
        "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, utc_now()),
        )


def _seed_watchlist(conn: sqlite3.Connection) -> None:
    """Insert the 10 default tickers if the user's watchlist is empty."""
    count = conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
    ).fetchone()[0]
    if count == 0:
        now = utc_now()
        conn.executemany(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            [(new_uuid(), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_TICKERS],
        )
