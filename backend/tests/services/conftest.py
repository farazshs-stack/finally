"""Shared fixtures for service-layer tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from app.db.connection import get_connection
from app.db.init import init_db
from app.market import PriceCache


@pytest.fixture()
def tmp_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    return db_file


@pytest.fixture()
def db_conn(tmp_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    init_db()
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture()
def seeded_cache() -> PriceCache:
    """PriceCache pre-seeded with realistic prices for the 10 default tickers."""
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
