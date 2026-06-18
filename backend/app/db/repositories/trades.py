"""Repository for the trades table (append-only trade log)."""

from __future__ import annotations

import sqlite3
from typing import Literal, TypedDict

from ..schema import DEFAULT_USER_ID
from ..utils import new_uuid, round_money, round_qty, utc_now

TradeSide = Literal["buy", "sell"]


class Trade(TypedDict):
    id: str
    user_id: str
    ticker: str
    side: str          # "buy" | "sell"
    quantity: float
    price: float
    executed_at: str


def insert_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: TradeSide,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
) -> Trade:
    """Append a trade record.

    Args:
        conn: Open SQLite connection.
        ticker: Ticker symbol (normalised to upper-case).
        side: "buy" or "sell".
        quantity: Number of shares (fractional supported).
        price: Execution price per share.
        user_id: User identifier.

    Returns:
        The newly inserted Trade dict.

    Raises:
        ValueError: If side is not "buy" or "sell".
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")

    ticker = ticker.upper()
    quantity = round_qty(quantity)
    price = round_money(price)
    trade_id = new_uuid()
    now = utc_now()

    conn.execute(
        """
        INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (trade_id, user_id, ticker, side, quantity, price, now),
    )

    return Trade(
        id=trade_id,
        user_id=user_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=now,
    )


def list_trades(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    ticker: str | None = None,
    limit: int | None = None,
) -> list[Trade]:
    """Return trades for a user, optionally filtered by ticker, newest first.

    Args:
        conn: Open SQLite connection.
        user_id: User identifier.
        ticker: If provided, filter to this ticker only.
        limit: Maximum number of rows to return (None = all).

    Returns:
        List of Trade dicts ordered by executed_at DESC.
    """
    query = """
        SELECT id, user_id, ticker, side, quantity, price, executed_at
        FROM trades
        WHERE user_id = ?
    """
    params: list = [user_id]

    if ticker is not None:
        query += " AND ticker = ?"
        params.append(ticker.upper())

    query += " ORDER BY executed_at DESC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [_row_to_trade(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_trade(row: sqlite3.Row) -> Trade:
    return Trade(
        id=row["id"],
        user_id=row["user_id"],
        ticker=row["ticker"],
        side=row["side"],
        quantity=row["quantity"],
        price=row["price"],
        executed_at=row["executed_at"],
    )
