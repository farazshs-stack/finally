"""Unit tests for the deterministic mock LLM (app.llm.mock)."""

from __future__ import annotations

from app.llm.mock import get_mock_response


class TestBuyRule:
    def test_buy_with_qty_and_ticker(self):
        r = get_mock_response("buy 5 AAPL")
        assert len(r.trades) == 1
        assert r.trades[0].side == "buy"
        assert r.trades[0].ticker == "AAPL"
        assert r.trades[0].quantity == 5.0
        assert "AAPL" in r.message
        assert r.watchlist_changes == []

    def test_buy_default_qty_when_no_number(self):
        r = get_mock_response("buy MSFT please")
        assert r.trades[0].quantity == 1.0
        assert r.trades[0].ticker == "MSFT"

    def test_buy_case_insensitive(self):
        r = get_mock_response("Buy 10 tsla")
        assert r.trades[0].ticker == "TSLA"
        assert r.trades[0].quantity == 10.0

    def test_buy_message_contains_ticker_and_qty(self):
        r = get_mock_response("buy 3 NVDA")
        assert "NVDA" in r.message
        assert "3" in r.message


class TestSellRule:
    def test_sell_with_qty_and_ticker(self):
        r = get_mock_response("sell 2 GOOGL")
        assert len(r.trades) == 1
        assert r.trades[0].side == "sell"
        assert r.trades[0].ticker == "GOOGL"
        assert r.trades[0].quantity == 2.0
        assert r.watchlist_changes == []

    def test_sell_default_qty(self):
        r = get_mock_response("sell META")
        assert r.trades[0].quantity == 1.0
        assert r.trades[0].ticker == "META"

    def test_sell_message_correct(self):
        r = get_mock_response("sell 7 V")
        assert "Selling" in r.message
        assert "V" in r.message


class TestAddWatchlistRule:
    def test_add_ticker(self):
        r = get_mock_response("add PYPL to my watchlist")
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].action == "add"
        assert r.watchlist_changes[0].ticker == "PYPL"
        assert r.trades == []

    def test_add_message_correct(self):
        r = get_mock_response("add PYPL")
        assert "Added" in r.message
        assert "PYPL" in r.message


class TestRemoveWatchlistRule:
    def test_remove_ticker(self):
        r = get_mock_response("remove NFLX from watchlist")
        assert len(r.watchlist_changes) == 1
        assert r.watchlist_changes[0].action == "remove"
        assert r.watchlist_changes[0].ticker == "NFLX"
        assert r.trades == []

    def test_delete_keyword(self):
        r = get_mock_response("delete AMZN")
        assert r.watchlist_changes[0].action == "remove"
        assert r.watchlist_changes[0].ticker == "AMZN"

    def test_remove_message_correct(self):
        r = get_mock_response("remove TSLA")
        assert "Removed" in r.message
        assert "TSLA" in r.message


class TestFallbackRule:
    def test_unrecognised_message(self):
        r = get_mock_response("how is my portfolio doing?")
        assert r.trades == []
        assert r.watchlist_changes == []
        assert len(r.message) > 0

    def test_empty_message_fallback(self):
        r = get_mock_response("")
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_generic_analysis_fallback(self):
        r = get_mock_response("analyse my risk exposure")
        assert r.trades == []
        assert "healthy" in r.message.lower() or len(r.message) > 0


class TestBuySellPrecedence:
    def test_buy_takes_precedence_over_other_words(self):
        # "buy" appears before "sell" — should match buy rule
        r = get_mock_response("buy and then sell 5 AAPL")
        assert r.trades[0].side == "buy"
