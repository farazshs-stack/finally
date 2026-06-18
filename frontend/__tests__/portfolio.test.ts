import { describe, it, expect } from "vitest";
import { computeLiveTotal } from "@/hooks/usePortfolio";
import type { Position } from "@/lib/types";

describe("computeLiveTotal", () => {
  const positions: Position[] = [
    {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 180,
      current_price: 190,
      market_value: 1900,
      unrealized_pnl: 100,
      pnl_percent: 5.56,
    },
    {
      ticker: "GOOGL",
      quantity: 5,
      avg_cost: 160,
      current_price: 170,
      market_value: 850,
      unrealized_pnl: 50,
      pnl_percent: 6.25,
    },
  ];

  it("computes total from live prices when available", () => {
    const prices = {
      AAPL: { price: 200 },
      GOOGL: { price: 175 },
    };
    const total = computeLiveTotal(positions, prices, 1000);
    // AAPL: 10 * 200 = 2000, GOOGL: 5 * 175 = 875, cash: 1000 → total = 3875
    expect(total).toBe(3875);
  });

  it("falls back to current_price when no live price", () => {
    const prices = {};
    const total = computeLiveTotal(positions, prices, 1000);
    // AAPL: 10 * 190 = 1900, GOOGL: 5 * 170 = 850, cash: 1000 → total = 3750
    expect(total).toBe(3750);
  });

  it("uses live price for some, fallback for others", () => {
    const prices = {
      AAPL: { price: 200 },
    };
    const total = computeLiveTotal(positions, prices, 500);
    // AAPL: 10 * 200 = 2000, GOOGL: 5 * 170 = 850, cash: 500 → total = 3350
    expect(total).toBe(3350);
  });

  it("returns cash when no positions", () => {
    const total = computeLiveTotal([], {}, 10000);
    expect(total).toBe(10000);
  });

  it("handles zero quantity gracefully", () => {
    const zeroPosns: Position[] = [
      {
        ticker: "AAPL",
        quantity: 0,
        avg_cost: 180,
        current_price: 190,
        market_value: 0,
        unrealized_pnl: 0,
        pnl_percent: 0,
      },
    ];
    const total = computeLiveTotal(zeroPosns, {}, 5000);
    expect(total).toBe(5000);
  });
});
