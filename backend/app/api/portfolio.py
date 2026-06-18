"""Portfolio API router.

Endpoints
---------
GET  /api/portfolio           -> PortfolioResponse
POST /api/portfolio/trade     -> TradeResponse
GET  /api/portfolio/history   -> list[SnapshotOut]
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.db import get_connection
from app.services.portfolio import (
    TradeError,
    execute_trade,
    get_history,
    get_portfolio,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: Literal["buy", "sell"]

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be greater than zero")
        return v


class PositionOut(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    pnl_percent: float


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[PositionOut]
    total_value: float
    total_unrealized_pnl: float


class TradeOut(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class TradeResponse(BaseModel):
    success: bool
    message: str
    trade: TradeOut | None = None


class SnapshotOut(BaseModel):
    id: str
    total_value: float
    recorded_at: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=PortfolioResponse)
def get_portfolio_endpoint(request: Request) -> PortfolioResponse:
    """Return current positions valued at live cache prices plus cash balance."""
    cache = request.app.state.price_cache
    with get_connection() as conn:
        data = get_portfolio(cache, conn)
    return PortfolioResponse(
        cash_balance=data["cash"],
        positions=[PositionOut(**p) for p in data["positions"]],
        total_value=data["total_value"],
        total_unrealized_pnl=data["total_unrealized_pnl"],
    )


@router.post("/trade", response_model=TradeResponse)
def trade_endpoint(body: TradeRequest, request: Request) -> TradeResponse:
    """Execute a market order (instant fill at current cache price).

    Returns a JSON success envelope on success.
    Returns HTTP 400 with detail message on validation failure.
    """
    from datetime import datetime, timezone

    cache = request.app.state.price_cache
    try:
        with get_connection() as conn:
            result = execute_trade(
                ticker=body.ticker,
                side=body.side,
                quantity=body.quantity,
                cache=cache,
                conn=conn,
            )
    except TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Trade executed: %s %s x%.4f @ %.2f", body.side, body.ticker, body.quantity, result["price"])
    executed_at = datetime.now(timezone.utc).isoformat()
    return TradeResponse(
        success=True,
        message=f"{result['side'].capitalize()} {result['quantity']} {result['ticker']} @ ${result['price']:.2f}",
        trade=TradeOut(
            ticker=result["ticker"],
            side=result["side"],
            quantity=result["quantity"],
            price=result["price"],
            executed_at=executed_at,
        ),
    )


@router.get("/history", response_model=list[SnapshotOut])
def history_endpoint() -> list[SnapshotOut]:
    """Return portfolio value snapshots ordered oldest-first for the P&L chart."""
    with get_connection() as conn:
        snaps = get_history(conn)
    return [SnapshotOut(**s) for s in snaps]
