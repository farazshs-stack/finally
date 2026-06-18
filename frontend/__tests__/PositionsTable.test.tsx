import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PositionsTable } from "@/components/PositionsTable";
import type { Position, PriceMap } from "@/lib/types";

const mockPositions: Position[] = [
  {
    ticker: "AAPL",
    quantity: 10,
    avg_cost: 180.0,
    current_price: 190.0,
    market_value: 1900.0,
    unrealized_pnl: 100.0,
    pnl_percent: 5.56,
  },
  {
    ticker: "TSLA",
    quantity: 5,
    avg_cost: 250.0,
    current_price: 240.0,
    market_value: 1200.0,
    unrealized_pnl: -50.0,
    pnl_percent: -4.0,
  },
];

const mockPrices: PriceMap = {
  AAPL: {
    ticker: "AAPL",
    price: 195.0,
    previous_price: 190.0,
    timestamp: Date.now() / 1000,
    change: 5.0,
    change_percent: 2.63,
    direction: "up",
  },
};

describe("PositionsTable", () => {
  it("renders the positions table", () => {
    render(<PositionsTable positions={mockPositions} prices={mockPrices} />);
    expect(screen.getByTestId("positions-table")).toBeTruthy();
  });

  it("displays all tickers in positions", () => {
    render(<PositionsTable positions={mockPositions} prices={mockPrices} />);
    expect(screen.getByText("AAPL")).toBeTruthy();
    expect(screen.getByText("TSLA")).toBeTruthy();
  });

  it("uses live price from prices prop when available", () => {
    render(<PositionsTable positions={mockPositions} prices={mockPrices} />);
    // AAPL live price is $195 from mockPrices; avg cost $180, qty 10
    // Live P&L = (195 - 180) * 10 = +$150
    const table = screen.getByTestId("positions-table");
    expect(table.textContent).toContain("195");
  });

  it("falls back to current_price when no live price", () => {
    render(<PositionsTable positions={mockPositions} prices={{}} />);
    // TSLA has no live price, falls back to current_price = $240
    const table = screen.getByTestId("positions-table");
    expect(table.textContent).toContain("240");
  });

  it("shows empty state when no positions", () => {
    render(<PositionsTable positions={[]} prices={{}} />);
    expect(screen.getByText(/No positions/)).toBeTruthy();
  });

  it("computes live P&L correctly using live prices", () => {
    render(<PositionsTable positions={mockPositions} prices={mockPrices} />);
    // AAPL: qty=10, avg_cost=180, live_price=195 → P&L = +150
    const table = screen.getByTestId("positions-table");
    expect(table.textContent).toContain("+$150");
  });
});
