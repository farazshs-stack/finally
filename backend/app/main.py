"""FinAlly — FastAPI application entry point.

Startup sequence
----------------
1. Load .env from the project root.
2. init_db() — create tables & seed default data (idempotent).
3. Build PriceCache and MarketDataSource.
4. Load watchlist tickers from DB (union with defaults) and start the source.
5. Schedule a 30-second background task that records portfolio snapshots.

Shutdown sequence
-----------------
1. Cancel the snapshot background task.
2. await source.stop().

app.state attributes (available to all route handlers via ``request.app.state``)
----------------------------------------------------------------------------------
    app.state.price_cache   : PriceCache        — live price store
    app.state.market_source : MarketDataSource   — running data source

Router registration order
--------------------------
    /api/stream/prices  ← SSE market data stream
    /api/portfolio      ← portfolio REST endpoints
    /api/watchlist      ← watchlist REST endpoints
    /api/chat           ← CHAT ROUTER (LLM engineer adds this — see comment below)
    /api/health         ← health check
    /                   ← StaticFiles catch-all (Next.js export)
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root BEFORE any other imports read env-vars.
# File layout: backend/app/main.py  =>  project root is three levels up.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

from fastapi import FastAPI  # noqa: E402 (must be after dotenv)
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api.portfolio import router as portfolio_router  # noqa: E402
from app.api.watchlist import router as watchlist_router  # noqa: E402
from app.db import get_connection, init_db, list_watchlist  # noqa: E402
from app.market import PriceCache, create_market_data_source, create_stream_router  # noqa: E402
from app.services.portfolio import record_snapshot  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Default tickers to always track (union with whatever is in the DB watchlist)
_DEFAULT_TICKERS: frozenset[str] = frozenset(
    {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
)

# One shared cache — created at module level so the SSE router (built here)
# references the same object that lifespan populates and route handlers read.
_PRICE_CACHE = PriceCache()


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def _snapshot_loop(application: FastAPI, interval: int = 30) -> None:
    """Persist a portfolio-value snapshot every *interval* seconds."""
    while True:
        await asyncio.sleep(interval)
        try:
            cache = application.state.price_cache
            with get_connection() as conn:
                record_snapshot(cache, conn)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in snapshot background task")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI):  # type: ignore[type-arg]
    """Manage startup and graceful shutdown of background services."""

    # 1. Initialise the database (idempotent — safe to call on every restart)
    init_db()
    logger.info("Database initialised.")

    # 2. Wire the shared cache onto app.state
    application.state.price_cache = _PRICE_CACHE

    # 3. Create market data source (simulator unless MASSIVE_API_KEY is set)
    source = create_market_data_source(_PRICE_CACHE)
    application.state.market_source = source

    # 4. Resolve initial ticker set: DB watchlist ∪ default tickers
    with get_connection() as conn:
        db_tickers: set[str] = {e["ticker"] for e in list_watchlist(conn)}
    tickers = sorted(_DEFAULT_TICKERS | db_tickers)
    logger.info("Starting market data source for %d tickers: %s", len(tickers), tickers)
    await source.start(tickers)

    # 5. Start 30-second portfolio snapshot background task
    snap_task = asyncio.create_task(_snapshot_loop(application))

    logger.info(
        "FinAlly backend running on port %s.",
        os.environ.get("PORT", "8000"),
    )

    yield  # ── application is serving requests ──

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Shutting down FinAlly backend…")

    snap_task.cancel()
    try:
        await snap_task
    except asyncio.CancelledError:
        pass

    await source.stop()
    logger.info("Market data source stopped. Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FinAlly API",
    description="AI Trading Workstation — backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# 1. SSE market data stream — uses _PRICE_CACHE directly (same object as app.state.price_cache)
app.include_router(create_stream_router(_PRICE_CACHE))

# 2. Portfolio REST endpoints  (GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history)
app.include_router(portfolio_router)

# 3. Watchlist REST endpoints  (GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker})
app.include_router(watchlist_router)

# ---------------------------------------------------------------------------
# CHAT ROUTER — LLM Engineer: register your router here.
#
# When app/api/chat.py is ready, add these two lines:
#
#   from app.api.chat import router as chat_router
#   app.include_router(chat_router)
#
# The chat router should use:
#   - prefix="/api/chat"
#   - tags=["chat"]
#   - Access live prices via: request.app.state.price_cache
#   - Access the market source via: request.app.state.market_source
# ---------------------------------------------------------------------------

from app.api.chat import router as chat_router  # noqa: E402

app.include_router(chat_router)


# 4. Health check  (must appear AFTER all /api/* routes but BEFORE static mount)
@app.get("/api/health", tags=["system"])
def health() -> JSONResponse:
    """Liveness / readiness probe used by Docker and deployment platforms."""
    return JSONResponse({"status": "ok"})


# 5. Static file serving — Next.js static export (catch-all AFTER all /api routes)
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
