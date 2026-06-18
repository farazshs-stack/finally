"""Repository for the watchlist table."""

from __future__ import annotations

import sqlite3
from typing import TypedDict

from ..schema import DEFAULT_USER_ID
from ..utils import new_uuid, utc_now


class WatchlistEntry(TypedDict):
    id: str
    user_id: str
    ticker: str
    added_at: str


def list_watchlist(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID
) -> list[WatchlistEntry]:
    """Return all tickers in the user's watchlist, ordered by added_at.

    Args:
        conn: Open SQLite connection.
        user_id: User identifier.

    Returns:
        List of WatchlistEntry dicts (may be empty).
    """
    rows = conn.execute(
        "SELECT id, user_id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    ).fetchall()
    return [
        WatchlistEntry(
            id=r["id"], user_id=r["user_id"], ticker=r["ticker"], added_at=r["added_at"]
        )
        for r in rows
    ]


def add_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> WatchlistEntry:
    """Add a ticker to the watchlist.  No-op (returns existing) if already present.

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol (stored as-is; caller should normalise to upper-case).
        user_id: User identifier.

    Returns:
        The WatchlistEntry for the ticker (new or existing).
    """
    ticker = ticker.upper()
    existing = conn.execute(
        "SELECT id, user_id, ticker, added_at FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if existing:
        return WatchlistEntry(
            id=existing["id"],
            user_id=existing["user_id"],
            ticker=existing["ticker"],
            added_at=existing["added_at"],
        )

    entry_id = new_uuid()
    now = utc_now()
    conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (entry_id, user_id, ticker, now),
    )
    return WatchlistEntry(id=entry_id, user_id=user_id, ticker=ticker, added_at=now)


def remove_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> bool:
    """Remove a ticker from the watchlist.

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol (normalised to upper-case internally).
        user_id: User identifier.

    Returns:
        True if a row was deleted, False if ticker wasn't in the watchlist.
    """
    ticker = ticker.upper()
    result = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    return result.rowcount > 0


def ticker_in_watchlist(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> bool:
    """Return True if ticker is currently in the watchlist."""
    ticker = ticker.upper()
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    return row is not None
