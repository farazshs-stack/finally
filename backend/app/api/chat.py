"""Chat API router — POST /api/chat (§9).

Flow
----
1. Receive {message: str}.
2. Load live portfolio context and recent conversation history.
3. Dispatch to mock (LLM_MOCK=true) or real LLM.
4. Auto-execute trades and watchlist changes from the LLM response.
5. Persist user + assistant messages (assistant carries the actions JSON).
6. Return {message, actions} where actions records outcomes of each auto-execution.

Endpoint
--------
POST /api/chat
  Body:    {"message": "<user text>"}
  Returns: {"message": "<assistant reply>", "actions": [<ActionResult>, ...]}
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db import (
    get_connection,
    insert_message,
    list_recent_messages,
    list_watchlist,
)
from app.db.utils import new_uuid
from app.llm import build_messages, call_llm, get_mock_response
from app.llm.schema import ChatResponse
from app.market import PriceCache
from app.services.portfolio import TradeError, execute_trade, get_portfolio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str


class ActionResult(BaseModel):
    """Outcome of a single auto-executed trade or watchlist change (internal use)."""

    type: str  # "trade" | "watchlist"
    # Trade fields
    ticker: str | None = None
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    cash_after: float | None = None
    # Watchlist fields
    action: str | None = None
    # Shared
    success: bool = True
    error: str | None = None


class ExecutedTradeOut(BaseModel):
    """Executed trade result in the frontend-facing shape."""

    ticker: str
    side: str
    quantity: float
    price: float | None = None
    success: bool = True
    error: str | None = None


class WatchlistChangeOut(BaseModel):
    """Watchlist change result in the frontend-facing shape."""

    ticker: str
    action: str
    success: bool = True


class ChatActionsOut(BaseModel):
    """Grouped actions for the frontend."""

    trades: list[ExecutedTradeOut] = []
    watchlist_changes: list[WatchlistChangeOut] = []


class ChatApiResponse(BaseModel):
    id: str
    role: str = "assistant"
    content: str
    actions: ChatActionsOut | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "").lower() == "true"


def _get_watchlist_prices(cache: PriceCache, conn) -> dict[str, float | None]:  # type: ignore[type-arg]
    """Return {ticker: live_price | None} for every watchlist entry."""
    entries = list_watchlist(conn)
    return {e["ticker"]: cache.get_price(e["ticker"]) for e in entries}


async def _apply_watchlist_change(
    ticker: str,
    action: str,
    request: Request,
    conn,  # type: ignore[type-arg]
) -> ActionResult:
    """Add or remove a ticker from the watchlist.

    Mirrors the logic in app/api/watchlist.py so that the same seed-price
    and market-source registration happen when the LLM makes the change.
    """
    from app.api.watchlist import UNKNOWN_TICKER_SEED_PRICE, _validate_ticker_format
    from app.db import add_ticker, remove_ticker

    ticker = ticker.upper()

    # Validate format (silent no-op for obviously bad tickers from the LLM)
    try:
        _validate_ticker_format(ticker)
    except Exception as exc:
        return ActionResult(
            type="watchlist",
            ticker=ticker,
            action=action,
            success=False,
            error=str(exc),
        )

    cache: PriceCache = request.app.state.price_cache
    source = request.app.state.market_source

    if action == "add":
        add_ticker(conn, ticker)
        conn.commit()
        if cache.get(ticker) is None:
            cache.update(ticker, UNKNOWN_TICKER_SEED_PRICE)
        await source.add_ticker(ticker)
        logger.info("Chat: added watchlist ticker %s", ticker)
        return ActionResult(type="watchlist", ticker=ticker, action="add", success=True)

    if action == "remove":
        removed = remove_ticker(conn, ticker)
        conn.commit()
        if removed:
            await source.remove_ticker(ticker)
            cache.remove(ticker)
            logger.info("Chat: removed watchlist ticker %s", ticker)
        return ActionResult(
            type="watchlist",
            ticker=ticker,
            action="remove",
            success=removed,
            error=None if removed else f"{ticker} was not on the watchlist.",
        )

    return ActionResult(
        type="watchlist",
        ticker=ticker,
        action=action,
        success=False,
        error=f"Unknown watchlist action {action!r}.",
    )


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


@router.post("", response_model=ChatApiResponse)
async def post_chat(body: ChatRequest, request: Request) -> ChatApiResponse:
    """Receive a user message, call the LLM, auto-execute actions, persist history."""
    user_message = body.message.strip()
    if not user_message:
        return ChatApiResponse(
            id=new_uuid(),
            role="assistant",
            content="Please enter a message.",
            actions=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    cache: PriceCache = request.app.state.price_cache

    with get_connection() as conn:
        # --- Build context ---
        portfolio = get_portfolio(cache, conn)
        watchlist_prices = _get_watchlist_prices(cache, conn)
        history = list_recent_messages(conn, n=20)

        # --- Persist user message ---
        insert_message(conn, "user", user_message)
        conn.commit()

    # --- Call LLM (or mock) ---
    if _is_mock_mode():
        llm_response: ChatResponse = get_mock_response(user_message)
    else:
        messages = build_messages(user_message, portfolio, watchlist_prices, history)
        llm_response = call_llm(messages)

    # --- Auto-execute actions ---
    actions: list[ActionResult] = []

    with get_connection() as conn:
        # Execute trades
        for trade in llm_response.trades:
            try:
                result = execute_trade(
                    ticker=trade.ticker,
                    side=trade.side,
                    quantity=trade.quantity,
                    cache=cache,
                    conn=conn,
                )
                actions.append(
                    ActionResult(
                        type="trade",
                        ticker=result["ticker"],
                        side=result["side"],
                        quantity=result["quantity"],
                        price=result["price"],
                        cash_after=result["cash_after"],
                        success=True,
                    )
                )
                logger.info(
                    "Chat auto-trade: %s %s x%.4f @ %.2f",
                    result["side"],
                    result["ticker"],
                    result["quantity"],
                    result["price"],
                )
            except TradeError as exc:
                logger.warning("Chat trade failed: %s", exc)
                actions.append(
                    ActionResult(
                        type="trade",
                        ticker=trade.ticker,
                        side=trade.side,
                        quantity=trade.quantity,
                        success=False,
                        error=str(exc),
                    )
                )

        # Execute watchlist changes (each needs the async source calls)
        for change in llm_response.watchlist_changes:
            wl_result = await _apply_watchlist_change(
                change.ticker, change.action, request, conn
            )
            actions.append(wl_result)

        # --- Persist assistant message with actions ---
        actions_payload = [a.model_dump(exclude_none=False) for a in actions] if actions else None
        insert_message(conn, "assistant", llm_response.message, actions=actions_payload)
        conn.commit()

    # Build the structured actions output for the frontend
    trade_outs: list[ExecutedTradeOut] = []
    watchlist_outs: list[WatchlistChangeOut] = []
    for a in actions:
        if a.type == "trade":
            trade_outs.append(
                ExecutedTradeOut(
                    ticker=a.ticker or "",
                    side=a.side or "",
                    quantity=a.quantity or 0.0,
                    price=a.price,
                    success=a.success,
                    error=a.error,
                )
            )
        elif a.type == "watchlist":
            watchlist_outs.append(
                WatchlistChangeOut(
                    ticker=a.ticker or "",
                    action=a.action or "",
                    success=a.success,
                )
            )

    actions_out: ChatActionsOut | None = None
    if trade_outs or watchlist_outs:
        actions_out = ChatActionsOut(trades=trade_outs, watchlist_changes=watchlist_outs)

    return ChatApiResponse(
        id=new_uuid(),
        role="assistant",
        content=llm_response.message,
        actions=actions_out,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
