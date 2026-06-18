"""Tests for the positions repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories.positions import (
    delete_position,
    get_all_positions,
    get_position,
    upsert_position,
)
from app.db.schema import DEFAULT_USER_ID


class TestGetAllPositions:
    def test_empty_initially(self, db_conn: sqlite3.Connection) -> None:
        positions = get_all_positions(db_conn)
        assert positions == []

    def test_returns_all_after_inserts(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "AAPL", quantity=10, avg_cost=180.0)
        upsert_position(db_conn, "GOOGL", quantity=5, avg_cost=170.0)
        db_conn.commit()
        positions = get_all_positions(db_conn)
        assert len(positions) == 2
        tickers = [p["ticker"] for p in positions]
        assert "AAPL" in tickers
        assert "GOOGL" in tickers


class TestGetPosition:
    def test_returns_none_if_no_position(self, db_conn: sqlite3.Connection) -> None:
        assert get_position(db_conn, "AAPL") is None

    def test_returns_position_after_insert(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "AAPL", quantity=10, avg_cost=180.0)
        db_conn.commit()
        pos = get_position(db_conn, "AAPL")
        assert pos is not None
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == pytest.approx(10.0)
        assert pos["avg_cost"] == pytest.approx(180.0)

    def test_case_insensitive_lookup(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "aapl", quantity=1, avg_cost=190.0)
        db_conn.commit()
        pos = get_position(db_conn, "AAPL")
        assert pos is not None


class TestUpsertPosition:
    def test_insert_creates_row(self, db_conn: sqlite3.Connection) -> None:
        pos = upsert_position(db_conn, "TSLA", quantity=5, avg_cost=250.0)
        db_conn.commit()
        assert pos["ticker"] == "TSLA"
        assert pos["quantity"] == pytest.approx(5.0)
        assert pos["avg_cost"] == pytest.approx(250.0)
        assert pos["id"]

    def test_update_changes_quantity_and_cost(self, db_conn: sqlite3.Connection) -> None:
        first = upsert_position(db_conn, "TSLA", quantity=5, avg_cost=250.0)
        db_conn.commit()
        second = upsert_position(db_conn, "TSLA", quantity=10, avg_cost=260.0)
        db_conn.commit()
        # id must be preserved
        assert first["id"] == second["id"]
        # values updated
        pos = get_position(db_conn, "TSLA")
        assert pos["quantity"] == pytest.approx(10.0)
        assert pos["avg_cost"] == pytest.approx(260.0)

    def test_only_one_row_per_user_ticker(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "MSFT", quantity=3, avg_cost=300.0)
        upsert_position(db_conn, "MSFT", quantity=6, avg_cost=310.0)
        db_conn.commit()
        count = db_conn.execute(
            "SELECT COUNT(*) FROM positions WHERE ticker='MSFT' AND user_id=?",
            (DEFAULT_USER_ID,),
        ).fetchone()[0]
        assert count == 1

    def test_rounds_quantity(self, db_conn: sqlite3.Connection) -> None:
        pos = upsert_position(db_conn, "NVDA", quantity=3.1234567, avg_cost=500.0)
        assert pos["quantity"] == pytest.approx(round(3.1234567, 6))

    def test_rounds_avg_cost(self, db_conn: sqlite3.Connection) -> None:
        pos = upsert_position(db_conn, "NVDA", quantity=1, avg_cost=500.1234567)
        assert pos["avg_cost"] == pytest.approx(round(500.1234567, 6))

    def test_normalises_ticker_to_uppercase(self, db_conn: sqlite3.Connection) -> None:
        pos = upsert_position(db_conn, "nvda", quantity=2, avg_cost=500.0)
        assert pos["ticker"] == "NVDA"


class TestDeletePosition:
    def test_delete_existing(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "META", quantity=4, avg_cost=400.0)
        db_conn.commit()
        deleted = delete_position(db_conn, "META")
        db_conn.commit()
        assert deleted is True
        assert get_position(db_conn, "META") is None

    def test_delete_nonexistent_returns_false(self, db_conn: sqlite3.Connection) -> None:
        deleted = delete_position(db_conn, "XYZZY")
        assert deleted is False

    def test_delete_only_own_user(self, db_conn: sqlite3.Connection) -> None:
        upsert_position(db_conn, "JPM", quantity=1, avg_cost=100.0, user_id="other")
        db_conn.commit()
        # default user deletes their own (non-existent) — should not affect other user
        delete_position(db_conn, "JPM")
        db_conn.commit()
        pos = get_position(db_conn, "JPM", user_id="other")
        assert pos is not None
