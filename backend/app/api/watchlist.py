"""Watchlist API router.

Endpoints
---------
GET    /api/watchlist          -> list[WatchlistEntryOut]
POST   /api/watchlist          -> WatchlistEntryOut
DELETE /api/watchlist/{ticker} -> RemoveResponse

Unknown-ticker seed rule (§13.A.1)
-----------------------------------
When a user adds a ticker that is not in the simulator's SEED_PRICES dict, the
simulator uses DEFAULT_PARAMS (sigma=0.25, mu=0.05) for GBM.  The starting
price injected into the PriceCache is a flat $100.00.  This sentinel is
documented in SEED_PRICES.DEFAULT_PARAMS and needs no special validation —
the simulator will pick it up on the next tick.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.db import add_ticker, get_connection, list_watchlist, remove_ticker
from app.market import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# Maximum ticker symbol length; reject obvious nonsense early
_TICKER_RE = re.compile(r"^[A-Z]{1,10}$")

# Flat seed price for tickers not in the simulator's SEED_PRICES table (§13.A.1)
UNKNOWN_TICKER_SEED_PRICE: float = 100.0


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AddTickerRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.strip().upper()


class WatchlistEntryOut(BaseModel):
    ticker: str
    price: float | None
    change_percent: float | None
    direction: str | None


class WatchlistResponse(BaseModel):
    watchlist: list[WatchlistEntryOut]


class RemoveResponse(BaseModel):
    removed: bool
    ticker: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_ticker_format(ticker: str) -> None:
    """Raise HTTPException(422) if the ticker contains invalid characters."""
    if not _TICKER_RE.match(ticker):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid ticker symbol {ticker!r}. "
                "Must be 1–10 uppercase letters (A-Z) with no spaces or digits."
            ),
        )


def _entry_out(ticker: str, cache: PriceCache) -> WatchlistEntryOut:
    update = cache.get(ticker)
    if update is None:
        return WatchlistEntryOut(ticker=ticker, price=None, change_percent=None, direction=None)
    return WatchlistEntryOut(
        ticker=ticker,
        price=update.price,
        change_percent=update.change_percent,
        direction=update.direction,
    )


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=list[WatchlistEntryOut])
def get_watchlist(request: Request) -> list[WatchlistEntryOut]:
    """Return all watchlist tickers with their latest cached price."""
    cache: PriceCache = request.app.state.price_cache
    with get_connection() as conn:
        entries = list_watchlist(conn)
    return [_entry_out(e["ticker"], cache) for e in entries]


@router.post("", response_model=WatchlistEntryOut, status_code=201)
async def add_watchlist_ticker(body: AddTickerRequest, request: Request) -> WatchlistEntryOut:
    """Add a ticker to the watchlist.

    - Normalises to upper-case.
    - Validates format (letters only, 1-10 chars).
    - Seeds PriceCache at $100 for unknown tickers so the SSE stream includes
      them immediately (before the simulator emits its first tick).
    - Tells the market data source to begin tracking the ticker.
    """
    ticker = body.ticker
    _validate_ticker_format(ticker)

    cache: PriceCache = request.app.state.price_cache
    source = request.app.state.market_source

    with get_connection() as conn:
        add_ticker(conn, ticker)
        conn.commit()

    # Seed cache immediately for unknown tickers so the SSE stream has a price
    if cache.get(ticker) is None:
        cache.update(ticker, UNKNOWN_TICKER_SEED_PRICE)
        logger.info("Seeded unknown ticker %s at $%.2f", ticker, UNKNOWN_TICKER_SEED_PRICE)

    # Start tracking in the market data source (simulator or Massive)
    await source.add_ticker(ticker)

    logger.info("Added ticker to watchlist: %s", ticker)
    return _entry_out(ticker, cache)


@router.delete("/{ticker}", response_model=RemoveResponse)
async def remove_watchlist_ticker(ticker: str, request: Request) -> RemoveResponse:
    """Remove a ticker from the watchlist, stop tracking it, and evict from cache."""
    ticker = ticker.strip().upper()
    _validate_ticker_format(ticker)

    cache: PriceCache = request.app.state.price_cache
    source = request.app.state.market_source

    with get_connection() as conn:
        removed = remove_ticker(conn, ticker)
        conn.commit()

    if removed:
        await source.remove_ticker(ticker)
        cache.remove(ticker)
        logger.info("Removed ticker from watchlist: %s", ticker)

    return RemoveResponse(removed=removed, ticker=ticker)
