"""Tests for the watchlist API endpoints.

GET    /api/watchlist
POST   /api/watchlist
DELETE /api/watchlist/{ticker}
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------


def test_get_watchlist_returns_defaults(client):
    """Default watchlist has the 10 seeded tickers returned as a list."""
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    tickers = [e["ticker"] for e in data]
    assert len(tickers) == 10
    for ticker in ("AAPL", "GOOGL", "MSFT", "NVDA"):
        assert ticker in tickers


def test_get_watchlist_includes_price(client):
    """Each entry includes a price sourced from the cache."""
    data = client.get("/api/watchlist").json()
    entry = next(e for e in data if e["ticker"] == "AAPL")
    assert entry["price"] == 190.00
    assert entry["direction"] == "flat"  # first update direction


def test_get_watchlist_response_shape(client):
    """Each watchlist entry has required fields."""
    data = client.get("/api/watchlist").json()
    entry = data[0]
    for key in ("ticker", "price", "change_percent", "direction"):
        assert key in entry


# ---------------------------------------------------------------------------
# POST /api/watchlist
# ---------------------------------------------------------------------------


def test_add_ticker_success(client, seeded_cache):
    """Adding a new ticker returns 201 with entry details."""
    # PYPL is not in the default list
    resp = client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "PYPL"
    # Should have been seeded at $100
    assert data["price"] == 100.00


def test_add_ticker_seeded_at_100(client, seeded_cache):
    """Unknown tickers are seeded at $100 in the cache (§13.A.1)."""
    client.post("/api/watchlist", json={"ticker": "FAKESTOCK"})
    assert seeded_cache.get_price("FAKESTOCK") == 100.00


def test_add_ticker_lowercase_normalised(client):
    """Lowercase ticker input is normalised to uppercase."""
    resp = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 201
    assert resp.json()["ticker"] == "PYPL"


def test_add_ticker_duplicate_is_idempotent(client):
    """Adding a ticker that is already in the watchlist does not error."""
    resp1 = client.post("/api/watchlist", json={"ticker": "AAPL"})
    resp2 = client.post("/api/watchlist", json={"ticker": "AAPL"})
    # Both should succeed (add_ticker is idempotent per DB layer docs)
    assert resp1.status_code == 201
    assert resp2.status_code == 201


def test_add_ticker_invalid_format_returns_422(client):
    """Symbols containing digits or special chars are rejected."""
    resp = client.post("/api/watchlist", json={"ticker": "AAP L"})
    assert resp.status_code == 422


def test_add_ticker_too_long_returns_422(client):
    """Ticker symbols longer than 10 characters are rejected."""
    resp = client.post("/api/watchlist", json={"ticker": "TOOLONGSYMBOL"})
    assert resp.status_code == 422


def test_add_ticker_appears_in_watchlist(client):
    """Newly added ticker appears in subsequent GET /api/watchlist."""
    client.post("/api/watchlist", json={"ticker": "PYPL"})
    data = client.get("/api/watchlist").json()
    tickers = [e["ticker"] for e in data]
    assert "PYPL" in tickers


def test_add_ticker_calls_source_add(client, mock_source):
    """Adding a ticker triggers source.add_ticker(ticker)."""
    client.post("/api/watchlist", json={"ticker": "PYPL"})
    mock_source.add_ticker.assert_awaited_with("PYPL")


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------


def test_remove_ticker_success(client):
    """Removing a default ticker returns removed=True."""
    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] is True
    assert data["ticker"] == "AAPL"


def test_remove_ticker_not_in_list_returns_false(client):
    """Removing a ticker not in the list returns removed=False (no error)."""
    resp = client.delete("/api/watchlist/PYPL")
    assert resp.status_code == 200
    assert resp.json()["removed"] is False


def test_remove_ticker_disappears_from_watchlist(client):
    """Removed ticker no longer appears in GET /api/watchlist."""
    client.delete("/api/watchlist/AAPL")
    data = client.get("/api/watchlist").json()
    tickers = [e["ticker"] for e in data]
    assert "AAPL" not in tickers


def test_remove_ticker_calls_source_remove(client, mock_source):
    """Removing a ticker triggers source.remove_ticker(ticker)."""
    client.delete("/api/watchlist/AAPL")
    mock_source.remove_ticker.assert_awaited_with("AAPL")


def test_remove_ticker_evicts_from_cache(client, seeded_cache):
    """Cache entry is removed after DELETE."""
    assert seeded_cache.get("AAPL") is not None
    client.delete("/api/watchlist/AAPL")
    assert seeded_cache.get("AAPL") is None


def test_remove_ticker_lowercase_accepted(client):
    """Lowercase ticker in URL path is normalised and processed."""
    resp = client.delete("/api/watchlist/aapl")
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "AAPL"


def test_remove_ticker_invalid_format_returns_422(client):
    """Symbols with invalid characters in path return 422."""
    resp = client.delete("/api/watchlist/AA PL")
    assert resp.status_code in (422, 404)  # FastAPI may 404 before validation
