"""Tests for the portfolio API endpoints.

GET  /api/portfolio
POST /api/portfolio/trade
GET  /api/portfolio/history
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------


def test_get_portfolio_empty(client):
    """Fresh portfolio returns $10k cash, no positions."""
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == pytest.approx(10_000.00, abs=0.01)
    assert data["positions"] == []
    assert data["total_value"] == pytest.approx(10_000.00, abs=0.01)
    assert data["total_unrealized_pnl"] == 0.0


def test_get_portfolio_response_shape(client):
    """Response has all required keys."""
    data = client.get("/api/portfolio").json()
    for key in ("cash_balance", "positions", "total_value", "total_unrealized_pnl"):
        assert key in data


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade — buy
# ---------------------------------------------------------------------------


def test_buy_trade_success(client):
    """Successful buy returns success envelope with trade details."""
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "buy"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["message"], str)
    assert data["trade"] is not None
    trade = data["trade"]
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 5.0
    assert trade["price"] == pytest.approx(190.00)
    assert "executed_at" in trade


def test_buy_creates_position(client):
    """After a buy the position shows up in GET /api/portfolio."""
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "buy"})
    data = client.get("/api/portfolio").json()
    tickers = [p["ticker"] for p in data["positions"]]
    assert "AAPL" in tickers


def test_buy_insufficient_cash_returns_400(client):
    """Trying to buy more than cash allows returns HTTP 400."""
    resp = client.post("/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 100, "side": "buy"})
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


def test_buy_lowercase_ticker_normalised(client):
    """Lowercase ticker symbols are accepted and normalised."""
    resp = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 1, "side": "buy"})
    assert resp.status_code == 200
    assert resp.json()["trade"]["ticker"] == "AAPL"


def test_buy_zero_quantity_returns_422(client):
    """Zero quantity is a validation error."""
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 0, "side": "buy"})
    assert resp.status_code == 422


def test_buy_negative_quantity_returns_422(client):
    """Negative quantity is a validation error."""
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": -1, "side": "buy"}
    )
    assert resp.status_code == 422


def test_buy_invalid_side_returns_422(client):
    """Invalid side value is a Pydantic validation error."""
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "hold"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade — sell
# ---------------------------------------------------------------------------


def test_sell_no_position_returns_400(client):
    """Selling a ticker with no position returns HTTP 400."""
    resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert resp.status_code == 400
    assert "No position" in resp.json()["detail"]


def test_sell_insufficient_shares_returns_400(client):
    """Selling more shares than owned returns HTTP 400."""
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "buy"})
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 100, "side": "sell"}
    )
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


def test_sell_all_removes_position(client):
    """Selling all shares removes the position from the portfolio."""
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "buy"})
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"})
    data = client.get("/api/portfolio").json()
    tickers = [p["ticker"] for p in data["positions"]]
    assert "AAPL" not in tickers


def test_sell_partial_keeps_position(client):
    """Selling a portion of shares keeps the position with reduced quantity."""
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 4, "side": "sell"})
    data = client.get("/api/portfolio").json()
    pos = next(p for p in data["positions"] if p["ticker"] == "AAPL")
    assert pos["quantity"] == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------


def test_history_returns_list(client):
    """History endpoint returns a list directly (may be empty initially)."""
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_history_has_snapshot_after_trade(client):
    """After a trade, at least one snapshot exists in history."""
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    resp = client.get("/api/portfolio/history")
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    snap = data[0]
    assert "id" in snap
    assert "total_value" in snap
    assert "recorded_at" in snap
