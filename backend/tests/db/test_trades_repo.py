"""Tests for the trades repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories.trades import insert_trade, list_trades
from app.db.schema import DEFAULT_USER_ID


class TestInsertTrade:
    def test_insert_buy(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "AAPL", "buy", quantity=10, price=185.0)
        db_conn.commit()
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == pytest.approx(10.0)
        assert trade["price"] == pytest.approx(185.0)
        assert trade["id"]
        assert trade["executed_at"]

    def test_insert_sell(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "GOOGL", "sell", quantity=5, price=172.0)
        db_conn.commit()
        assert trade["side"] == "sell"

    def test_normalises_ticker(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "aapl", "buy", 1, 180.0)
        assert trade["ticker"] == "AAPL"

    def test_invalid_side_raises(self, db_conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="side must be"):
            insert_trade(db_conn, "AAPL", "hold", 1, 180.0)  # type: ignore[arg-type]

    def test_rounds_quantity_and_price(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "TSLA", "buy", quantity=2.1234567, price=250.1234567)
        assert trade["quantity"] == pytest.approx(round(2.1234567, 6))
        assert trade["price"] == pytest.approx(round(250.1234567, 6))

    def test_user_id_default(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "V", "buy", 3, 220.0)
        assert trade["user_id"] == DEFAULT_USER_ID

    def test_custom_user_id(self, db_conn: sqlite3.Connection) -> None:
        trade = insert_trade(db_conn, "V", "buy", 3, 220.0, user_id="alice")
        assert trade["user_id"] == "alice"


class TestListTrades:
    def test_empty_initially(self, db_conn: sqlite3.Connection) -> None:
        trades = list_trades(db_conn)
        assert trades == []

    def test_returns_all_trades(self, db_conn: sqlite3.Connection) -> None:
        insert_trade(db_conn, "AAPL", "buy", 10, 185.0)
        insert_trade(db_conn, "GOOGL", "sell", 5, 172.0)
        db_conn.commit()
        trades = list_trades(db_conn)
        assert len(trades) == 2

    def test_ordered_newest_first(self, db_conn: sqlite3.Connection) -> None:
        insert_trade(db_conn, "AAPL", "buy", 1, 180.0)
        insert_trade(db_conn, "GOOGL", "buy", 1, 170.0)
        db_conn.commit()
        trades = list_trades(db_conn)
        # newest first
        assert trades[0]["executed_at"] >= trades[1]["executed_at"]

    def test_filter_by_ticker(self, db_conn: sqlite3.Connection) -> None:
        insert_trade(db_conn, "AAPL", "buy", 1, 180.0)
        insert_trade(db_conn, "GOOGL", "buy", 1, 170.0)
        db_conn.commit()
        aapl_trades = list_trades(db_conn, ticker="AAPL")
        assert all(t["ticker"] == "AAPL" for t in aapl_trades)
        assert len(aapl_trades) == 1

    def test_filter_by_ticker_case_insensitive(self, db_conn: sqlite3.Connection) -> None:
        insert_trade(db_conn, "AAPL", "buy", 1, 180.0)
        db_conn.commit()
        trades = list_trades(db_conn, ticker="aapl")
        assert len(trades) == 1

    def test_limit(self, db_conn: sqlite3.Connection) -> None:
        for i in range(5):
            insert_trade(db_conn, "AAPL", "buy", i + 1, 180.0)
        db_conn.commit()
        trades = list_trades(db_conn, limit=3)
        assert len(trades) == 3

    def test_user_isolation(self, db_conn: sqlite3.Connection) -> None:
        insert_trade(db_conn, "AAPL", "buy", 1, 180.0, user_id="alice")
        insert_trade(db_conn, "MSFT", "buy", 1, 300.0, user_id="bob")
        db_conn.commit()
        alice_trades = list_trades(db_conn, user_id="alice")
        assert len(alice_trades) == 1
        assert alice_trades[0]["ticker"] == "AAPL"
