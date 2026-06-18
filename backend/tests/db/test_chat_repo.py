"""Tests for the chat_messages repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.db.repositories.chat import (
    insert_message,
    list_all_messages,
    list_recent_messages,
)
from app.db.schema import DEFAULT_USER_ID


class TestInsertMessage:
    def test_insert_user_message(self, db_conn: sqlite3.Connection) -> None:
        msg = insert_message(db_conn, role="user", content="Hello!")
        db_conn.commit()
        assert msg["role"] == "user"
        assert msg["content"] == "Hello!"
        assert msg["actions"] is None
        assert msg["user_id"] == DEFAULT_USER_ID
        assert msg["id"]
        assert msg["created_at"]

    def test_insert_assistant_message_with_actions(self, db_conn: sqlite3.Connection) -> None:
        actions = {
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
            "watchlist_changes": [],
        }
        msg = insert_message(db_conn, role="assistant", content="Buying AAPL.", actions=actions)
        db_conn.commit()
        assert msg["role"] == "assistant"
        assert msg["actions"] == actions

    def test_actions_round_trip_through_json(self, db_conn: sqlite3.Connection) -> None:
        actions = {"trades": [{"ticker": "TSLA", "side": "sell", "quantity": 5}]}
        insert_message(db_conn, role="assistant", content="Sold TSLA.", actions=actions)
        db_conn.commit()
        messages = list_all_messages(db_conn)
        stored_actions = messages[-1]["actions"]
        assert stored_actions == actions

    def test_invalid_role_raises(self, db_conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="role must be"):
            insert_message(db_conn, role="system", content="Oops")  # type: ignore[arg-type]

    def test_custom_user_id(self, db_conn: sqlite3.Connection) -> None:
        msg = insert_message(db_conn, role="user", content="Hi", user_id="alice")
        assert msg["user_id"] == "alice"


class TestListAllMessages:
    def test_empty_initially(self, db_conn: sqlite3.Connection) -> None:
        msgs = list_all_messages(db_conn)
        assert msgs == []

    def test_returns_in_chronological_order(self, db_conn: sqlite3.Connection) -> None:
        insert_message(db_conn, role="user", content="First")
        insert_message(db_conn, role="assistant", content="Second")
        db_conn.commit()
        msgs = list_all_messages(db_conn)
        assert len(msgs) == 2
        assert msgs[0]["content"] == "First"
        assert msgs[1]["content"] == "Second"

    def test_user_isolation(self, db_conn: sqlite3.Connection) -> None:
        insert_message(db_conn, role="user", content="Alice msg", user_id="alice")
        insert_message(db_conn, role="user", content="Bob msg", user_id="bob")
        db_conn.commit()
        alice_msgs = list_all_messages(db_conn, user_id="alice")
        assert len(alice_msgs) == 1
        assert alice_msgs[0]["content"] == "Alice msg"


class TestListRecentMessages:
    def test_returns_at_most_n_messages(self, db_conn: sqlite3.Connection) -> None:
        for i in range(25):
            insert_message(db_conn, role="user", content=f"msg {i}")
        db_conn.commit()
        recent = list_recent_messages(db_conn, n=10)
        assert len(recent) == 10

    def test_returns_most_recent_n_in_chronological_order(
        self, db_conn: sqlite3.Connection
    ) -> None:
        for i in range(25):
            insert_message(db_conn, role="user", content=f"msg {i}")
        db_conn.commit()
        recent = list_recent_messages(db_conn, n=5)
        assert len(recent) == 5
        # The last inserted message must be the final element (rowid tiebreaker)
        contents = [m["content"] for m in recent]
        assert contents[-1] == "msg 24"

    def test_fewer_than_n_returns_all(self, db_conn: sqlite3.Connection) -> None:
        insert_message(db_conn, role="user", content="only one")
        db_conn.commit()
        recent = list_recent_messages(db_conn, n=20)
        assert len(recent) == 1

    def test_default_n_is_20(self, db_conn: sqlite3.Connection) -> None:
        for i in range(30):
            insert_message(db_conn, role="user", content=f"msg {i}")
        db_conn.commit()
        recent = list_recent_messages(db_conn)  # default n=20
        assert len(recent) == 20
