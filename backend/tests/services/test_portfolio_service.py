"""Unit tests for app.services.portfolio.

Covers:
- Buy happy path
- Buy: insufficient cash
- Sell happy path
- Sell: no position
- Sell: insufficient shares
- Sell all shares removes the position row
- Avg-cost math on repeated buys
- Portfolio valuation and P&L calculation
- record_snapshot integration
- get_history ordering
"""

from __future__ import annotations

import pytest

from app.db import get_position, list_snapshots, list_trades
from app.market import PriceCache
from app.services.portfolio import (
    TradeError,
    execute_trade,
    get_history,
    get_portfolio,
    record_snapshot,
)

# ---------------------------------------------------------------------------
# execute_trade — buy path
# ---------------------------------------------------------------------------


def test_buy_happy_path(db_conn, seeded_cache):
    """Buying shares deducts cash and creates a position."""
    result = execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)

    assert result["ticker"] == "AAPL"
    assert result["side"] == "buy"
    assert result["quantity"] == 10.0
    assert result["price"] == 190.00

    expected_cash = 10_000.00 - 10 * 190.00
    assert abs(result["cash_after"] - expected_cash) < 0.01

    pos = get_position(db_conn, "AAPL")
    assert pos is not None
    assert pos["quantity"] == 10.0
    assert pos["avg_cost"] == 190.00

    trades = list_trades(db_conn)
    assert len(trades) == 1
    assert trades[0]["side"] == "buy"


def test_buy_updates_avg_cost(db_conn, seeded_cache):
    """Second buy at a different price updates the weighted-average cost."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    # Bump price for the second buy
    seeded_cache.update("AAPL", 200.00)
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)

    pos = get_position(db_conn, "AAPL")
    assert pos["quantity"] == 20.0
    expected_avg = (10 * 190.00 + 10 * 200.00) / 20
    assert abs(pos["avg_cost"] - expected_avg) < 0.01


def test_buy_insufficient_cash(db_conn, seeded_cache):
    """Buying more than cash allows raises TradeError."""
    with pytest.raises(TradeError, match="Insufficient cash"):
        # 1 share of NVDA at $800 is fine; 100 shares at $800 = $80k > $10k
        execute_trade("NVDA", "buy", 100, seeded_cache, db_conn)


def test_buy_zero_quantity_raises(db_conn, seeded_cache):
    """Zero quantity is rejected."""
    with pytest.raises(TradeError, match="greater than zero"):
        execute_trade("AAPL", "buy", 0, seeded_cache, db_conn)


def test_buy_negative_quantity_raises(db_conn, seeded_cache):
    """Negative quantity is rejected."""
    with pytest.raises(TradeError, match="greater than zero"):
        execute_trade("AAPL", "buy", -5, seeded_cache, db_conn)


def test_buy_no_price_in_cache(db_conn):
    """Ticker with no cached price raises TradeError."""
    empty_cache = PriceCache()
    with pytest.raises(TradeError, match="No price available"):
        execute_trade("XYZ", "buy", 1, empty_cache, db_conn)


# ---------------------------------------------------------------------------
# execute_trade — sell path
# ---------------------------------------------------------------------------


def test_sell_happy_path(db_conn, seeded_cache):
    """Selling shares increases cash and reduces the position."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    result = execute_trade("AAPL", "sell", 5, seeded_cache, db_conn)

    assert result["side"] == "sell"
    assert result["quantity"] == 5.0

    pos = get_position(db_conn, "AAPL")
    assert pos is not None
    assert pos["quantity"] == 5.0

    # Cash = 10000 - 10*190 + 5*190
    expected_cash = 10_000.00 - 10 * 190 + 5 * 190
    assert abs(result["cash_after"] - expected_cash) < 0.01


def test_sell_all_removes_position(db_conn, seeded_cache):
    """Selling all shares deletes the position row."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    execute_trade("AAPL", "sell", 10, seeded_cache, db_conn)

    pos = get_position(db_conn, "AAPL")
    assert pos is None


def test_sell_no_position_raises(db_conn, seeded_cache):
    """Selling a ticker with no position raises TradeError."""
    with pytest.raises(TradeError, match="No position"):
        execute_trade("AAPL", "sell", 1, seeded_cache, db_conn)


def test_sell_insufficient_shares_raises(db_conn, seeded_cache):
    """Selling more shares than owned raises TradeError."""
    execute_trade("AAPL", "buy", 5, seeded_cache, db_conn)
    with pytest.raises(TradeError, match="Insufficient shares"):
        execute_trade("AAPL", "sell", 10, seeded_cache, db_conn)


def test_sell_at_profit(db_conn, seeded_cache):
    """Selling at a higher price yields a gain."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    seeded_cache.update("AAPL", 210.00)
    result = execute_trade("AAPL", "sell", 10, seeded_cache, db_conn)

    # Profit = 10 * (210 - 190) = 200
    expected_cash = 10_000.00 - 10 * 190 + 10 * 210
    assert abs(result["cash_after"] - expected_cash) < 0.01


def test_sell_at_loss(db_conn, seeded_cache):
    """Selling at a lower price yields a loss (cash still updated correctly)."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    seeded_cache.update("AAPL", 180.00)
    result = execute_trade("AAPL", "sell", 10, seeded_cache, db_conn)

    expected_cash = 10_000.00 - 10 * 190 + 10 * 180
    assert abs(result["cash_after"] - expected_cash) < 0.01


def test_invalid_side_raises(db_conn, seeded_cache):
    """Invalid side raises TradeError."""
    with pytest.raises(TradeError, match="Invalid side"):
        execute_trade("AAPL", "hold", 1, seeded_cache, db_conn)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_portfolio
# ---------------------------------------------------------------------------


def test_portfolio_no_positions(db_conn, seeded_cache):
    """Empty portfolio returns cash and no positions."""
    data = get_portfolio(seeded_cache, db_conn)

    assert data["cash"] == pytest.approx(10_000.00, abs=0.01)
    assert data["positions"] == []
    assert data["total_value"] == pytest.approx(10_000.00, abs=0.01)
    assert data["total_unrealized_pnl"] == 0.0


def test_portfolio_with_position(db_conn, seeded_cache):
    """Portfolio correctly values a position and computes P&L."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    # Bump price to create unrealised gain
    seeded_cache.update("AAPL", 200.00)

    data = get_portfolio(seeded_cache, db_conn)

    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10.0
    assert pos["avg_cost"] == pytest.approx(190.00)
    assert pos["current_price"] == pytest.approx(200.00)
    assert pos["market_value"] == pytest.approx(2000.00)
    assert pos["unrealized_pnl"] == pytest.approx(100.00)  # (200-190)*10
    assert pos["pnl_percent"] == pytest.approx((100 / 1900) * 100, rel=1e-3)

    cash = 10_000.00 - 10 * 190
    assert data["cash"] == pytest.approx(cash, abs=0.01)
    assert data["total_value"] == pytest.approx(cash + 2000.00, abs=0.01)


def test_portfolio_pnl_at_loss(db_conn, seeded_cache):
    """Unrealised P&L is negative when the price has fallen below avg_cost."""
    execute_trade("AAPL", "buy", 10, seeded_cache, db_conn)
    seeded_cache.update("AAPL", 180.00)

    data = get_portfolio(seeded_cache, db_conn)
    pos = data["positions"][0]
    assert pos["unrealized_pnl"] == pytest.approx(-100.00, abs=0.01)
    assert pos["pnl_percent"] < 0


# ---------------------------------------------------------------------------
# record_snapshot and get_history
# ---------------------------------------------------------------------------


def test_record_snapshot_inserts_row(db_conn, seeded_cache):
    record_snapshot(seeded_cache, db_conn)
    snaps = list_snapshots(db_conn)
    assert len(snaps) == 1
    assert snaps[0]["total_value"] == pytest.approx(10_000.00, abs=0.01)


def test_get_history_oldest_first(db_conn, seeded_cache):
    """get_history returns snapshots in chronological order."""
    record_snapshot(seeded_cache, db_conn)
    execute_trade("AAPL", "buy", 5, seeded_cache, db_conn)  # execute_trade records another
    history = get_history(db_conn)
    assert len(history) >= 2
    # Verify ascending order
    for i in range(len(history) - 1):
        assert history[i]["recorded_at"] <= history[i + 1]["recorded_at"]


def test_execute_trade_records_snapshot(db_conn, seeded_cache):
    """execute_trade automatically records a portfolio snapshot."""
    snaps_before = list_snapshots(db_conn)
    execute_trade("AAPL", "buy", 1, seeded_cache, db_conn)
    snaps_after = list_snapshots(db_conn)
    assert len(snaps_after) == len(snaps_before) + 1
