"""Repository for the positions table.

Positions represent current holdings — one row per (user_id, ticker).
The avg_cost is the volume-weighted average purchase price.
"""

from __future__ import annotations

import sqlite3
from typing import TypedDict

from ..schema import DEFAULT_USER_ID
from ..utils import new_uuid, round_money, round_qty, utc_now


class Position(TypedDict):
    id: str
    user_id: str
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str


def get_all_positions(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID
) -> list[Position]:
    """Return all positions for a user ordered by ticker.

    Args:
        conn: Open SQLite connection.
        user_id: User identifier.

    Returns:
        List of Position dicts (may be empty).
    """
    rows = conn.execute(
        """
        SELECT id, user_id, ticker, quantity, avg_cost, updated_at
        FROM positions
        WHERE user_id = ?
        ORDER BY ticker
        """,
        (user_id,),
    ).fetchall()
    return [_row_to_position(r) for r in rows]


def get_position(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> Position | None:
    """Return a single position, or None if the user holds no shares.

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol (normalised to upper-case).
        user_id: User identifier.
    """
    ticker = ticker.upper()
    row = conn.execute(
        """
        SELECT id, user_id, ticker, quantity, avg_cost, updated_at
        FROM positions
        WHERE user_id = ? AND ticker = ?
        """,
        (user_id, ticker),
    ).fetchone()
    return _row_to_position(row) if row else None


def upsert_position(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    user_id: str = DEFAULT_USER_ID,
) -> Position:
    """Insert or update a position row.

    If a row for (user_id, ticker) already exists it is updated in-place
    (preserving the existing ``id``).  If it doesn't exist a new row is
    created.

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol (normalised to upper-case).
        quantity: New total quantity (should already be the resolved total).
        avg_cost: New weighted-average cost basis per share.
        user_id: User identifier.

    Returns:
        The updated Position.
    """
    ticker = ticker.upper()
    quantity = round_qty(quantity)
    avg_cost = round_money(avg_cost)
    now = utc_now()

    existing = conn.execute(
        "SELECT id FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE positions
            SET quantity = ?, avg_cost = ?, updated_at = ?
            WHERE user_id = ? AND ticker = ?
            """,
            (quantity, avg_cost, now, user_id, ticker),
        )
        row_id = existing["id"]
    else:
        row_id = new_uuid()
        conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row_id, user_id, ticker, quantity, avg_cost, now),
        )

    return Position(
        id=row_id,
        user_id=user_id,
        ticker=ticker,
        quantity=quantity,
        avg_cost=avg_cost,
        updated_at=now,
    )


def delete_position(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> bool:
    """Delete a position row (used when quantity reaches zero after a sell).

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol.
        user_id: User identifier.

    Returns:
        True if a row was deleted, False if no such position existed.
    """
    ticker = ticker.upper()
    result = conn.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_position(row: sqlite3.Row) -> Position:
    return Position(
        id=row["id"],
        user_id=row["user_id"],
        ticker=row["ticker"],
        quantity=row["quantity"],
        avg_cost=row["avg_cost"],
        updated_at=row["updated_at"],
    )
