"""Integration tests for POST /api/chat.

All tests run with LLM_MOCK=true and use the shared 'client' fixture from
tests/api/conftest.py (temp DB + seeded PriceCache + mock market source).

Covered scenarios
-----------------
1. Basic message returns a response (no trades/watchlist).
2. "buy 5 AAPL" auto-executes the trade and updates the portfolio.
3. A failing trade (insufficient cash) is reported in the response, not raised.
4. Watchlist add via chat adds the ticker to the DB and market source.
5. Conversation history is persisted (user + assistant messages in DB).
6. Empty message returns a graceful response.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_connection, list_all_messages, list_watchlist


@pytest.fixture(autouse=True)
def _set_llm_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")


# ---------------------------------------------------------------------------
# Basic response
# ---------------------------------------------------------------------------


class TestChatBasicResponse:
    def test_returns_200_with_message(self, client: TestClient):
        resp = client.post("/api/chat", json={"message": "how is my portfolio?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert isinstance(data["content"], str)
        assert len(data["content"]) > 0
        assert data["role"] == "assistant"
        assert "id" in data
        assert "created_at" in data

    def test_returns_actions_or_null(self, client: TestClient):
        resp = client.post("/api/chat", json={"message": "analyse my portfolio"})
        assert resp.status_code == 200
        data = resp.json()
        # actions is either None or a dict with trades/watchlist_changes
        assert "actions" in data
        assert data["actions"] is None or isinstance(data["actions"], dict)

    def test_empty_message_returns_prompt(self, client: TestClient):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data


# ---------------------------------------------------------------------------
# Trade execution
# ---------------------------------------------------------------------------


class TestChatTradeExecution:
    def test_buy_executes_trade_and_returns_action(self, client: TestClient, tmp_db_path):
        resp = client.post("/api/chat", json={"message": "buy 5 AAPL"})
        assert resp.status_code == 200
        data = resp.json()

        # The mock should return a buy action in the grouped actions shape
        assert data["actions"] is not None
        trade_actions = data["actions"]["trades"]
        assert len(trade_actions) == 1
        action = trade_actions[0]
        assert action["success"] is True
        assert action["ticker"] == "AAPL"
        assert action["side"] == "buy"
        assert action["quantity"] == 5.0

    def test_buy_updates_portfolio(self, client: TestClient, tmp_db_path):
        """After buying 5 AAPL @ $190, cash should decrease."""
        client.post("/api/chat", json={"message": "buy 5 AAPL"})

        # Check portfolio via API
        portfolio_resp = client.get("/api/portfolio")
        assert portfolio_resp.status_code == 200
        portfolio = portfolio_resp.json()

        # Cash should be less than $10000 (bought 5 AAPL @ 190 = $950)
        assert portfolio["cash_balance"] < 10000.0

        # AAPL position should exist
        tickers = [p["ticker"] for p in portfolio["positions"]]
        assert "AAPL" in tickers

    def test_buy_action_includes_price(self, client: TestClient):
        resp = client.post("/api/chat", json={"message": "buy 5 AAPL"})
        data = resp.json()
        assert data["actions"] is not None
        trade_actions = data["actions"]["trades"]
        assert len(trade_actions) == 1
        action = trade_actions[0]
        assert action["price"] is not None and action["price"] > 0


class TestChatTradeFailure:
    def test_insufficient_cash_reported_in_actions(self, client: TestClient):
        """Buying more than available cash should surface as a failed trade action."""
        # AAPL at $190 — buy 1000 shares = $190,000 >> $10,000 cash
        resp = client.post("/api/chat", json={"message": "buy 1000 AAPL"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["actions"] is not None
        trade_actions = data["actions"]["trades"]
        assert len(trade_actions) == 1
        action = trade_actions[0]
        assert action["success"] is False
        assert action["error"] is not None
        assert len(action["error"]) > 0

    def test_failed_trade_does_not_modify_portfolio(self, client: TestClient):
        """A failed trade must leave cash unchanged."""
        initial = client.get("/api/portfolio").json()["cash_balance"]
        client.post("/api/chat", json={"message": "buy 1000 AAPL"})
        after = client.get("/api/portfolio").json()["cash_balance"]
        assert after == initial


# ---------------------------------------------------------------------------
# Watchlist changes
# ---------------------------------------------------------------------------


class TestChatWatchlistChange:
    def test_add_ticker_via_chat(self, client: TestClient, tmp_db_path):
        resp = client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["actions"] is not None
        wl_actions = data["actions"]["watchlist_changes"]
        assert len(wl_actions) == 1
        assert wl_actions[0]["action"] == "add"
        assert wl_actions[0]["ticker"] == "PYPL"
        assert wl_actions[0]["success"] is True

    def test_add_ticker_persisted_to_db(self, client: TestClient, tmp_db_path):
        client.post("/api/chat", json={"message": "add PYPL to my watchlist"})

        with get_connection() as conn:
            watchlist = list_watchlist(conn)
        tickers = [e["ticker"] for e in watchlist]
        assert "PYPL" in tickers

    def test_add_ticker_registered_with_market_source(
        self, client: TestClient, tmp_db_path
    ):
        """Market source.add_ticker should be called for new watchlist tickers."""
        import app.main as main_module

        client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        # mock_source.add_ticker is an AsyncMock; check it was called with PYPL
        source = main_module.app.state.market_source
        # It may be called multiple times (lifespan + chat), find PYPL call
        call_args_list = [str(c) for c in source.add_ticker.call_args_list]
        assert any("PYPL" in arg for arg in call_args_list)


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------


class TestChatHistoryPersistence:
    def test_user_message_persisted(self, client: TestClient, tmp_db_path):
        client.post("/api/chat", json={"message": "analyse my portfolio"})

        with get_connection() as conn:
            messages = list_all_messages(conn)

        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any(m["content"] == "analyse my portfolio" for m in user_msgs)

    def test_assistant_message_persisted(self, client: TestClient, tmp_db_path):
        client.post("/api/chat", json={"message": "analyse my portfolio"})

        with get_connection() as conn:
            messages = list_all_messages(conn)

        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1

    def test_multiple_messages_accumulate(self, client: TestClient, tmp_db_path):
        client.post("/api/chat", json={"message": "analyse my portfolio"})
        client.post("/api/chat", json={"message": "analyse my portfolio"})

        with get_connection() as conn:
            messages = list_all_messages(conn)

        # 2 user + 2 assistant = 4 total
        assert len(messages) >= 4

    def test_assistant_actions_stored_in_db(self, client: TestClient, tmp_db_path):
        """The assistant message for a trade should have actions stored."""
        client.post("/api/chat", json={"message": "buy 5 AAPL"})

        with get_connection() as conn:
            messages = list_all_messages(conn)

        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1
        # At least one assistant message should have non-null actions
        assert any(m["actions"] is not None for m in assistant_msgs)
