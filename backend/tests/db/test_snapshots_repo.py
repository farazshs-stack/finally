"""Tests for the portfolio_snapshots repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories.snapshots import insert_snapshot, list_snapshots
from app.db.schema import DEFAULT_USER_ID


class TestInsertSnapshot:
    def test_insert_returns_snapshot(self, db_conn: sqlite3.Connection) -> None:
        snap = insert_snapshot(db_conn, total_value=10_500.0)
        db_conn.commit()
        assert snap["total_value"] == pytest.approx(10_500.0)
        assert snap["user_id"] == DEFAULT_USER_ID
        assert snap["id"]
        assert snap["recorded_at"]

    def test_rounds_total_value(self, db_conn: sqlite3.Connection) -> None:
        snap = insert_snapshot(db_conn, total_value=9999.1234567)
        assert snap["total_value"] == pytest.approx(round(9999.1234567, 6))

    def test_custom_user_id(self, db_conn: sqlite3.Connection) -> None:
        snap = insert_snapshot(db_conn, total_value=5000.0, user_id="alice")
        assert snap["user_id"] == "alice"


class TestListSnapshots:
    def test_empty_initially(self, db_conn: sqlite3.Connection) -> None:
        snaps = list_snapshots(db_conn)
        assert snaps == []

    def test_returns_snapshots_oldest_first(self, db_conn: sqlite3.Connection) -> None:
        insert_snapshot(db_conn, total_value=10_000.0)
        insert_snapshot(db_conn, total_value=10_500.0)
        insert_snapshot(db_conn, total_value=11_000.0)
        db_conn.commit()
        snaps = list_snapshots(db_conn)
        assert len(snaps) == 3
        # oldest first
        times = [s["recorded_at"] for s in snaps]
        assert times == sorted(times)

    def test_limit_returns_most_recent_n(self, db_conn: sqlite3.Connection) -> None:
        for v in [10_000, 10_500, 11_000, 11_500, 12_000]:
            insert_snapshot(db_conn, total_value=float(v))
        db_conn.commit()
        snaps = list_snapshots(db_conn, limit=3)
        assert len(snaps) == 3
        # The 3 most recent by insertion order, returned oldest-first
        values = [s["total_value"] for s in snaps]
        assert pytest.approx(12_000.0) in values

    def test_limit_result_still_oldest_first(self, db_conn: sqlite3.Connection) -> None:
        for v in [10_000, 10_500, 11_000]:
            insert_snapshot(db_conn, total_value=float(v))
        db_conn.commit()
        snaps = list_snapshots(db_conn, limit=2)
        times = [s["recorded_at"] for s in snaps]
        assert times == sorted(times)

    def test_user_isolation(self, db_conn: sqlite3.Connection) -> None:
        insert_snapshot(db_conn, total_value=10_000.0, user_id="alice")
        insert_snapshot(db_conn, total_value=20_000.0, user_id="bob")
        db_conn.commit()
        alice = list_snapshots(db_conn, user_id="alice")
        assert len(alice) == 1
        assert alice[0]["total_value"] == pytest.approx(10_000.0)
