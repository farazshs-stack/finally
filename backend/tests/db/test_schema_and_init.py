"""Tests for schema creation and lazy initialisation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db.connection import get_connection
from app.db.init import init_db
from app.db.schema import DEFAULT_TICKERS, DEFAULT_USER_ID


class TestSchemaCreation:
    """Verify that all expected tables exist after init_db()."""

    EXPECTED_TABLES = {
        "users_profile",
        "watchlist",
        "positions",
        "trades",
        "portfolio_snapshots",
        "chat_messages",
    }

    def test_all_tables_created(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {r["name"] for r in rows}
            assert self.EXPECTED_TABLES.issubset(names)
        finally:
            conn.close()

    def test_users_profile_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(users_profile)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "cash_balance", "created_at"}.issubset(cols)
        finally:
            conn.close()

    def test_watchlist_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(watchlist)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "user_id", "ticker", "added_at"}.issubset(cols)
        finally:
            conn.close()

    def test_positions_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(positions)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "user_id", "ticker", "quantity", "avg_cost", "updated_at"}.issubset(cols)
        finally:
            conn.close()

    def test_trades_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(trades)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "user_id", "ticker", "side", "quantity", "price", "executed_at"}.issubset(
                cols
            )
        finally:
            conn.close()

    def test_portfolio_snapshots_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(portfolio_snapshots)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "user_id", "total_value", "recorded_at"}.issubset(cols)
        finally:
            conn.close()

    def test_chat_messages_columns(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            info = conn.execute("PRAGMA table_info(chat_messages)").fetchall()
            cols = {r["name"] for r in info}
            assert {"id", "user_id", "role", "content", "actions", "created_at"}.issubset(cols)
        finally:
            conn.close()


class TestIdempotentInit:
    """init_db() is safe to call multiple times."""

    def test_double_init_no_error(self, initialized_db: Path) -> None:
        """Calling init_db() a second time must not raise."""
        init_db()  # second call — should be a no-op

    def test_double_init_preserves_seed(self, initialized_db: Path) -> None:
        """Second init must not duplicate or destroy seed data."""
        init_db()
        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
            ).fetchone()[0]
            assert count == len(DEFAULT_TICKERS)
        finally:
            conn.close()


class TestSeedCorrectness:
    """Verify the seeded defaults match the spec."""

    def test_default_user_profile_exists(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
            ).fetchone()
            assert row is not None
            assert row["cash_balance"] == pytest.approx(10_000.0)
        finally:
            conn.close()

    def test_default_watchlist_has_10_tickers(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
                (DEFAULT_USER_ID,),
            ).fetchall()
            tickers = [r["ticker"] for r in rows]
            assert len(tickers) == 10
        finally:
            conn.close()

    def test_default_watchlist_exact_tickers(self, initialized_db: Path) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
            ).fetchall()
            tickers = {r["ticker"] for r in rows}
            assert tickers == set(DEFAULT_TICKERS)
        finally:
            conn.close()

    def test_watchlist_ids_are_uuids(self, initialized_db: Path) -> None:
        """Each watchlist row must have a non-empty UUID-shaped id."""
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)).fetchall()
            for r in rows:
                assert uuid_pattern.match(r["id"]), f"Bad UUID: {r['id']}"
        finally:
            conn.close()
