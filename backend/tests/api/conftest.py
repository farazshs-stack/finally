"""Shared fixtures for API-layer tests.

Uses FastAPI's TestClient with a temporary database and a pre-seeded
PriceCache so tests run fully synchronously without a live market source.

Strategy
--------
The lifespan replaces app.state.price_cache with _PRICE_CACHE from main.py
and creates a real market data source.  To avoid network calls we:

1. Monkeypatch ``app.main._PRICE_CACHE`` to our seeded PriceCache *before*
   the TestClient starts (so the SSE router is already pointing at it).
2. Monkeypatch ``create_market_data_source`` to return our mock_source so no
   simulator or Massive client starts.
3. Monkeypatch the environment to unset MASSIVE_API_KEY (force simulator
   branch, though step 2 preempts it).
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.market import PriceCache


@pytest.fixture()
def tmp_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_api.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    # Remove MASSIVE_API_KEY so factory always returns the simulator branch
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    return db_file


@pytest.fixture()
def seeded_cache() -> PriceCache:
    cache = PriceCache()
    prices = {
        "AAPL": 190.00,
        "GOOGL": 175.00,
        "MSFT": 420.00,
        "AMZN": 185.00,
        "TSLA": 250.00,
        "NVDA": 800.00,
        "META": 500.00,
        "JPM": 195.00,
        "V": 280.00,
        "NFLX": 600.00,
    }
    for ticker, price in prices.items():
        cache.update(ticker, price)
    return cache


@pytest.fixture()
def mock_source() -> MagicMock:
    """A mock MarketDataSource — no network, no background threads."""
    source = MagicMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()
    source.stop = AsyncMock()
    source.start = AsyncMock()
    source.get_tickers = MagicMock(return_value=[])
    return source


@pytest.fixture()
def client(
    tmp_db_path: Path,
    seeded_cache: PriceCache,
    mock_source: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """TestClient wired with temp DB, seeded PriceCache, and mock market source.

    Monkeypatching order:
    1. Replace app.main._PRICE_CACHE with seeded_cache so both the SSE router
       (created at module-load with _PRICE_CACHE) and lifespan share the same
       object.
    2. Replace create_market_data_source in main so lifespan gets mock_source.
    3. Let the real lifespan run (init_db, source.start, snapshot task) but
       everything is mocked/temp so it is safe.
    """
    import app.main as main_module

    # 1. Swap the module-level cache for our seeded one
    monkeypatch.setattr(main_module, "_PRICE_CACHE", seeded_cache)

    # 2. Swap the factory so lifespan.source = mock_source
    monkeypatch.setattr(main_module, "create_market_data_source", lambda _cache: mock_source)

    # 3. Re-import the app *after* patching so the SSE router picks up the new cache
    #    (the router was already created with the old _PRICE_CACHE reference — we
    #    recreate the router by re-mounting, but that is invasive.  Instead, we simply
    #    replace the app.state references after startup via the TestClient context.)

    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        # After lifespan runs, app.state.price_cache == seeded_cache
        # (lifespan does: application.state.price_cache = _PRICE_CACHE, which is now seeded_cache)
        # app.state.market_source == mock_source (factory was patched)
        yield c
