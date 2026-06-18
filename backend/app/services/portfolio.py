"""Portfolio business-logic service.

Reused by the API layer and the LLM/chat engineer.  All DB mutations that
touch cash, positions or trades go through here so rounding and validation
are always applied consistently (§13.B.3).

Public API
----------
Classes
~~~~~~~
    TradeError          - raised on validation failure; maps to HTTP 400

Functions
~~~~~~~~~
    execute_trade(ticker, side, quantity, cache, conn, user_id) -> TradeResult
    get_portfolio(cache, conn, user_id) -> PortfolioData
    get_history(conn, user_id) -> list[SnapshotPoint]
    record_snapshot(cache, conn, user_id) -> None
"""

from __future__ import annotations

import sqlite3
from typing import Literal, TypedDict

from app.db import (
    delete_position,
    display_money,
    get_all_positions,
    get_cash_balance,
    get_position,
    insert_snapshot,
    insert_trade,
    list_snapshots,
    round_money,
    round_qty,
    update_cash_balance,
    upsert_position,
)
from app.market import PriceCache

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class TradeError(Exception):
    """Raised when a trade fails validation.

    The message is user-facing and will be forwarded to the HTTP 400 response.
    """


class PositionDetail(TypedDict):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    pnl_percent: float


class PortfolioData(TypedDict):
    cash: float
    positions: list[PositionDetail]
    total_value: float
    total_unrealized_pnl: float


class TradeResult(TypedDict):
    ticker: str
    side: str
    quantity: float
    price: float
    cash_after: float


class SnapshotPoint(TypedDict):
    id: str
    total_value: float
    recorded_at: str


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def execute_trade(
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    cache: PriceCache,
    conn: sqlite3.Connection,
    user_id: str = "default",
) -> TradeResult:
    """Validate and execute a market order at the current cached price.

    Steps:
    1. Look up the current price from the cache.
    2. Validate (buy: enough cash; sell: enough shares).
    3. Persist: upsert position, update cash, append trade record.
    4. Record a portfolio snapshot.

    Args:
        ticker:   Ticker symbol (normalised to upper-case internally).
        side:     "buy" or "sell".
        quantity: Number of shares (fractional allowed; must be > 0).
        cache:    Live price cache — price is read from here (instant fill).
        conn:     Open SQLite connection.
        user_id:  Defaults to "default" (single-user app).

    Returns:
        TradeResult with ticker, side, quantity, fill price, and post-trade cash.

    Raises:
        TradeError: On any validation failure (bad quantity, no price, etc.).
    """
    ticker = ticker.upper()
    side = side.lower()  # type: ignore[assignment]

    # --- Basic validation ---
    if side not in ("buy", "sell"):
        raise TradeError(f"Invalid side {side!r}: must be 'buy' or 'sell'.")

    quantity = round_qty(quantity)
    if quantity <= 0:
        raise TradeError("Quantity must be greater than zero.")

    # --- Price lookup ---
    current_price = cache.get_price(ticker)
    if current_price is None:
        raise TradeError(
            f"No price available for {ticker}. "
            "Add it to your watchlist first so the simulator can track it."
        )
    current_price = round_money(current_price)

    if side == "buy":
        _execute_buy(ticker, quantity, current_price, conn, user_id)
    else:
        _execute_sell(ticker, quantity, current_price, conn, user_id)

    # Record snapshot after every trade
    record_snapshot(cache, conn, user_id)

    cash_after = get_cash_balance(conn, user_id)
    return TradeResult(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=current_price,
        cash_after=cash_after,
    )


def get_portfolio(
    cache: PriceCache,
    conn: sqlite3.Connection,
    user_id: str = "default",
) -> PortfolioData:
    """Return a point-in-time portfolio snapshot valued at live cache prices.

    The frontend recomputes a streaming total on every SSE tick (§13.A.3);
    this endpoint provides the authoritative positions & cash from the DB
    valued at the latest cache prices.

    Returns:
        PortfolioData with cash, positions list, total_value and
        total_unrealized_pnl.
    """
    cash = get_cash_balance(conn, user_id)
    db_positions = get_all_positions(conn, user_id)

    positions: list[PositionDetail] = []
    total_market_value = 0.0
    total_unrealized_pnl = 0.0

    for pos in db_positions:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        avg_cost = pos["avg_cost"]

        current_price = cache.get_price(ticker)
        if current_price is None:
            # Fall back to avg_cost so valuation still makes sense
            current_price = avg_cost

        current_price = round_money(current_price)
        market_value = round_money(qty * current_price)
        cost_basis = round_money(qty * avg_cost)
        unrealized_pnl = round_money(market_value - cost_basis)
        pnl_percent = (
            round((unrealized_pnl / cost_basis) * 100, 4) if cost_basis != 0 else 0.0
        )

        positions.append(
            PositionDetail(
                ticker=ticker,
                quantity=qty,
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                pnl_percent=pnl_percent,
            )
        )

        total_market_value += market_value
        total_unrealized_pnl += unrealized_pnl

    total_value = round_money(cash + total_market_value)
    total_unrealized_pnl = round_money(total_unrealized_pnl)

    return PortfolioData(
        cash=cash,
        positions=positions,
        total_value=total_value,
        total_unrealized_pnl=total_unrealized_pnl,
    )


def get_history(
    conn: sqlite3.Connection,
    user_id: str = "default",
) -> list[SnapshotPoint]:
    """Return portfolio-value snapshots ordered oldest-first (chart-ready).

    Returns:
        List of SnapshotPoint dicts with total_value and recorded_at (ISO UTC).
    """
    rows = list_snapshots(conn, user_id)
    return [SnapshotPoint(id=r["id"], total_value=r["total_value"], recorded_at=r["recorded_at"]) for r in rows]


def record_snapshot(
    cache: PriceCache,
    conn: sqlite3.Connection,
    user_id: str = "default",
) -> None:
    """Compute current portfolio total value and persist a snapshot row.

    Called:
    - after every trade (inside execute_trade)
    - by the 30-second background task in main.py
    """
    data = get_portfolio(cache, conn, user_id)
    insert_snapshot(conn, data["total_value"], user_id)
    conn.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _execute_buy(
    ticker: str,
    quantity: float,
    price: float,
    conn: sqlite3.Connection,
    user_id: str,
) -> None:
    cost = round_money(quantity * price)
    cash = get_cash_balance(conn, user_id)

    # Use display_money for the "insufficient funds" comparison (§13.B.3)
    if display_money(cash) < display_money(cost):
        raise TradeError(
            f"Insufficient cash. Need ${display_money(cost):.2f} "
            f"but only ${display_money(cash):.2f} available."
        )

    existing = get_position(conn, ticker, user_id)
    if existing:
        old_qty = existing["quantity"]
        old_avg = existing["avg_cost"]
        new_qty = round_qty(old_qty + quantity)
        # Weighted-average cost basis
        new_avg = round_money((old_qty * old_avg + quantity * price) / new_qty)
    else:
        new_qty = quantity
        new_avg = price

    upsert_position(conn, ticker, new_qty, new_avg, user_id)
    new_cash = round_money(cash - cost)
    update_cash_balance(conn, new_cash, user_id)
    insert_trade(conn, ticker, "buy", quantity, price, user_id)
    conn.commit()


def _execute_sell(
    ticker: str,
    quantity: float,
    price: float,
    conn: sqlite3.Connection,
    user_id: str,
) -> None:
    existing = get_position(conn, ticker, user_id)
    if not existing:
        raise TradeError(f"No position in {ticker} to sell.")

    owned = existing["quantity"]
    if display_money(owned) < display_money(quantity):
        raise TradeError(
            f"Insufficient shares. You own {owned:.6f} {ticker} "
            f"but tried to sell {quantity:.6f}."
        )

    new_qty = round_qty(owned - quantity)
    proceeds = round_money(quantity * price)

    if new_qty <= 0:
        delete_position(conn, ticker, user_id)
    else:
        upsert_position(conn, ticker, new_qty, existing["avg_cost"], user_id)

    cash = get_cash_balance(conn, user_id)
    new_cash = round_money(cash + proceeds)
    update_cash_balance(conn, new_cash, user_id)
    insert_trade(conn, ticker, "sell", quantity, price, user_id)
    conn.commit()
