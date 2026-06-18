"""Tests for the profile repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories.profile import (
    ensure_profile,
    get_cash_balance,
    get_profile,
    update_cash_balance,
)
from app.db.schema import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID


class TestGetProfile:
    def test_returns_profile_after_init(self, db_conn: sqlite3.Connection) -> None:
        profile = get_profile(db_conn)
        assert profile is not None
        assert profile["id"] == DEFAULT_USER_ID
        assert profile["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE)

    def test_returns_none_for_unknown_user(self, db_conn: sqlite3.Connection) -> None:
        profile = get_profile(db_conn, user_id="ghost")
        assert profile is None

    def test_profile_has_created_at(self, db_conn: sqlite3.Connection) -> None:
        profile = get_profile(db_conn)
        assert profile is not None
        assert profile["created_at"]  # non-empty string


class TestUpdateCashBalance:
    def test_update_balance(self, db_conn: sqlite3.Connection) -> None:
        stored = update_cash_balance(db_conn, 5_000.0)
        db_conn.commit()
        assert stored == pytest.approx(5_000.0)
        profile = get_profile(db_conn)
        assert profile["cash_balance"] == pytest.approx(5_000.0)

    def test_update_rounds_to_6_places(self, db_conn: sqlite3.Connection) -> None:
        stored = update_cash_balance(db_conn, 1234.1234567)
        db_conn.commit()
        # Should be rounded to 6 decimal places
        assert stored == pytest.approx(round(1234.1234567, 6))

    def test_update_raises_for_missing_user(self, db_conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="No profile found"):
            update_cash_balance(db_conn, 100.0, user_id="nobody")

    def test_update_allows_zero_balance(self, db_conn: sqlite3.Connection) -> None:
        stored = update_cash_balance(db_conn, 0.0)
        assert stored == pytest.approx(0.0)


class TestGetCashBalance:
    def test_returns_balance(self, db_conn: sqlite3.Connection) -> None:
        bal = get_cash_balance(db_conn)
        assert bal == pytest.approx(DEFAULT_CASH_BALANCE)

    def test_returns_default_for_missing_user(self, db_conn: sqlite3.Connection) -> None:
        bal = get_cash_balance(db_conn, user_id="ghost")
        assert bal == DEFAULT_CASH_BALANCE


class TestEnsureProfile:
    def test_returns_existing(self, db_conn: sqlite3.Connection) -> None:
        p = ensure_profile(db_conn)
        assert p["id"] == DEFAULT_USER_ID

    def test_creates_if_missing(self, db_conn: sqlite3.Connection) -> None:
        p = ensure_profile(db_conn, user_id="brand_new")
        assert p["id"] == "brand_new"
        assert p["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE)
