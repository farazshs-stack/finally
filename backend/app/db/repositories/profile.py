"""Repository for users_profile table."""

from __future__ import annotations

import sqlite3
from typing import TypedDict

from ..schema import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID
from ..utils import round_money, utc_now


class UserProfile(TypedDict):
    id: str
    cash_balance: float
    created_at: str


def get_profile(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> UserProfile | None:
    """Return the user profile row, or None if it doesn't exist.

    Args:
        conn: Open SQLite connection.
        user_id: User identifier (defaults to "default").

    Returns:
        UserProfile dict or None.
    """
    row = conn.execute(
        "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return UserProfile(id=row["id"], cash_balance=row["cash_balance"], created_at=row["created_at"])


def update_cash_balance(
    conn: sqlite3.Connection,
    new_balance: float,
    user_id: str = DEFAULT_USER_ID,
) -> float:
    """Set the user's cash balance, rounded to storage precision.

    Args:
        conn: Open SQLite connection.
        new_balance: New cash amount (may be negative only if caller allows it).
        user_id: User identifier.

    Returns:
        The stored (rounded) balance.

    Raises:
        ValueError: If no profile row exists for user_id.
    """
    stored = round_money(new_balance)
    result = conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (stored, user_id),
    )
    if result.rowcount == 0:
        raise ValueError(f"No profile found for user_id={user_id!r}")
    return stored


def get_cash_balance(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    """Convenience: return cash balance or the default starting amount if not found."""
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    return row["cash_balance"] if row else DEFAULT_CASH_BALANCE


def ensure_profile(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> UserProfile:
    """Return existing profile or create it with defaults.

    Useful for tests and one-off scripts that skip init_db().
    """
    profile = get_profile(conn, user_id)
    if profile is None:
        conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (user_id, DEFAULT_CASH_BALANCE, utc_now()),
        )
        profile = get_profile(conn, user_id)
    return profile  # type: ignore[return-value]
