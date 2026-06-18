"""Tests for the watchlist repository."""

from __future__ import annotations

import sqlite3

from app.db.repositories.watchlist import (
    add_ticker,
    list_watchlist,
    remove_ticker,
    ticker_in_watchlist,
)
from app.db.schema import DEFAULT_TICKERS, DEFAULT_USER_ID


class TestListWatchlist:
    def test_returns_10_seed_tickers(self, db_conn: sqlite3.Connection) -> None:
        entries = list_watchlist(db_conn)
        assert len(entries) == 10

    def test_contains_seed_tickers(self, db_conn: sqlite3.Connection) -> None:
        entries = list_watchlist(db_conn)
        tickers = {e["ticker"] for e in entries}
        assert tickers == set(DEFAULT_TICKERS)

    def test_empty_for_unknown_user(self, db_conn: sqlite3.Connection) -> None:
        entries = list_watchlist(db_conn, user_id="ghost")
        assert entries == []


class TestAddTicker:
    def test_add_new_ticker(self, db_conn: sqlite3.Connection) -> None:
        entry = add_ticker(db_conn, "PYPL")
        db_conn.commit()
        assert entry["ticker"] == "PYPL"
        assert entry["user_id"] == DEFAULT_USER_ID
        assert entry["id"]  # non-empty

    def test_add_normalises_to_uppercase(self, db_conn: sqlite3.Connection) -> None:
        entry = add_ticker(db_conn, "pypl")
        assert entry["ticker"] == "PYPL"

    def test_add_existing_returns_existing(self, db_conn: sqlite3.Connection) -> None:
        first = add_ticker(db_conn, "PYPL")
        db_conn.commit()
        second = add_ticker(db_conn, "PYPL")
        # Same id — no duplicate row
        assert first["id"] == second["id"]
        # Only one row in DB
        count = db_conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE ticker = ? AND user_id = ?",
            ("PYPL", DEFAULT_USER_ID),
        ).fetchone()[0]
        assert count == 1

    def test_add_appears_in_list(self, db_conn: sqlite3.Connection) -> None:
        add_ticker(db_conn, "SHOP")
        db_conn.commit()
        entries = list_watchlist(db_conn)
        tickers = [e["ticker"] for e in entries]
        assert "SHOP" in tickers

    def test_unique_per_user(self, db_conn: sqlite3.Connection) -> None:
        """Same ticker for two different users creates two separate rows."""
        add_ticker(db_conn, "TSLA", user_id="user_a")
        add_ticker(db_conn, "TSLA", user_id="user_b")
        db_conn.commit()
        count = db_conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE ticker = 'TSLA'"
        ).fetchone()[0]
        # TSLA already exists for DEFAULT_USER_ID from seed + 2 new users
        assert count >= 2


class TestRemoveTicker:
    def test_remove_existing(self, db_conn: sqlite3.Connection) -> None:
        removed = remove_ticker(db_conn, "AAPL")
        db_conn.commit()
        assert removed is True
        assert not ticker_in_watchlist(db_conn, "AAPL")

    def test_remove_normalises_case(self, db_conn: sqlite3.Connection) -> None:
        removed = remove_ticker(db_conn, "aapl")
        db_conn.commit()
        assert removed is True

    def test_remove_nonexistent_returns_false(self, db_conn: sqlite3.Connection) -> None:
        removed = remove_ticker(db_conn, "DOESNOTEXIST")
        assert removed is False

    def test_remove_only_affects_own_user(self, db_conn: sqlite3.Connection) -> None:
        add_ticker(db_conn, "AAPL", user_id="other_user")
        db_conn.commit()
        remove_ticker(db_conn, "AAPL")  # removes default user's AAPL
        db_conn.commit()
        # other_user's AAPL must still exist
        assert ticker_in_watchlist(db_conn, "AAPL", user_id="other_user")


class TestTickerInWatchlist:
    def test_returns_true_for_seed_ticker(self, db_conn: sqlite3.Connection) -> None:
        assert ticker_in_watchlist(db_conn, "AAPL") is True

    def test_returns_false_for_unknown(self, db_conn: sqlite3.Connection) -> None:
        assert ticker_in_watchlist(db_conn, "XYZZY") is False

    def test_case_insensitive(self, db_conn: sqlite3.Connection) -> None:
        assert ticker_in_watchlist(db_conn, "aapl") is True
