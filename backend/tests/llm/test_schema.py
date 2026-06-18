"""Unit tests for app.llm.schema — Pydantic model parsing & validation."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.llm.schema import ChatResponse, TradeAction, WatchlistAction


class TestTradeAction:
    def test_normalises_ticker_to_upper(self):
        t = TradeAction(ticker="aapl", side="buy", quantity=5)
        assert t.ticker == "AAPL"

    def test_strips_whitespace_from_ticker(self):
        t = TradeAction(ticker="  MSFT  ", side="sell", quantity=2)
        assert t.ticker == "MSFT"

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=0)

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=-3)

    def test_rejects_invalid_side(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="hold", quantity=1)

    def test_fractional_quantity_allowed(self):
        t = TradeAction(ticker="TSLA", side="buy", quantity=0.5)
        assert t.quantity == 0.5


class TestWatchlistAction:
    def test_normalises_ticker(self):
        w = WatchlistAction(ticker="pypl", action="add")
        assert w.ticker == "PYPL"

    def test_rejects_invalid_action(self):
        with pytest.raises(ValidationError):
            WatchlistAction(ticker="AAPL", action="toggle")


class TestChatResponse:
    def test_minimal_valid_response(self):
        r = ChatResponse(message="hello")
        assert r.message == "hello"
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_full_response_from_json(self):
        raw = json.dumps(
            {
                "message": "Buying AAPL",
                "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
                "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
            }
        )
        r = ChatResponse.model_validate_json(raw)
        assert r.message == "Buying AAPL"
        assert len(r.trades) == 1
        assert r.trades[0].ticker == "AAPL"
        assert r.trades[0].side == "buy"
        assert r.trades[0].quantity == 10
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].ticker == "PYPL"
        assert r.watchlist_changes[0].action == "add"

    def test_response_without_optional_fields(self):
        raw = json.dumps({"message": "Hello!"})
        r = ChatResponse.model_validate_json(raw)
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_missing_message_fails(self):
        with pytest.raises(ValidationError):
            ChatResponse.model_validate_json(json.dumps({"trades": []}))

    def test_code_fence_stripped_via_parse_response(self):
        """Verify _parse_response in client handles code-fence wrapping."""
        from app.llm.client import _parse_response

        fenced = '```json\n{"message": "ok"}\n```'
        r = _parse_response(fenced)
        assert r.message == "ok"
