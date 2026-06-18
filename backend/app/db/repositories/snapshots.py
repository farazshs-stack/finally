"""Repository for the portfolio_snapshots table.

Snapshots record total portfolio value over time for the P&L chart.
They are written on every trade and optionally at a regular cadence
while a client is connected.
"""

from __future__ import annotations

import sqlite3
from typing import TypedDict

from ..schema import DEFAULT_USER_ID
from ..utils import new_uuid, round_money, utc_now


class PortfolioSnapshot(TypedDict):
    id: str
    user_id: str
    total_value: float
    recorded_at: str


def insert_snapshot(
    conn: sqlite3.Connection,
    total_value: float,
    user_id: str = DEFAULT_USER_ID,
) -> PortfolioSnapshot:
    """Insert a portfolio value snapshot.

    Args:
        conn: Open SQLite connection.
        total_value: Total portfolio value (cash + positions) at this moment.
        user_id: User identifier.

    Returns:
        The newly inserted PortfolioSnapshot dict.
    """
    snap_id = new_uuid()
    now = utc_now()
    value = round_money(total_value)

    conn.execute(
        """
        INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
        VALUES (?, ?, ?, ?)
        """,
        (snap_id, user_id, value, now),
    )

    return PortfolioSnapshot(
        id=snap_id,
        user_id=user_id,
        total_value=value,
        recorded_at=now,
    )


def list_snapshots(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[PortfolioSnapshot]:
    """Return portfolio snapshots ordered oldest→newest (for chart rendering).

    Args:
        conn: Open SQLite connection.
        user_id: User identifier.
        limit: Maximum rows (None = all).  When limiting, returns the *most
               recent* N rows still ordered oldest→newest.

    Returns:
        List of PortfolioSnapshot dicts.
    """
    if limit is not None:
        # Sub-query to pick the last N rows, then re-order ascending for charts.
        # rowid is used as a stable tiebreaker when recorded_at timestamps collide
        # (e.g., rapid test insertions within the same microsecond).
        query = """
            SELECT id, user_id, total_value, recorded_at
            FROM (
                SELECT id, user_id, total_value, recorded_at, rowid
                FROM portfolio_snapshots
                WHERE user_id = ?
                ORDER BY recorded_at DESC, rowid DESC
                LIMIT ?
            )
            ORDER BY recorded_at ASC, rowid ASC
        """
        rows = conn.execute(query, (user_id, limit)).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, user_id, total_value, recorded_at
            FROM portfolio_snapshots
            WHERE user_id = ?
            ORDER BY recorded_at ASC, rowid ASC
            """,
            (user_id,),
        ).fetchall()

    return [_row_to_snapshot(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_snapshot(row: sqlite3.Row) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        id=row["id"],
        user_id=row["user_id"],
        total_value=row["total_value"],
        recorded_at=row["recorded_at"],
    )
