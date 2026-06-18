import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WatchlistPanel } from "@/components/WatchlistPanel";
import type { WatchlistEntry, PriceMap, SparklinePoint } from "@/lib/types";

const mockWatchlist: WatchlistEntry[] = [
  { ticker: "AAPL", price: 190.5, change_percent: 0.5, direction: "up" },
  { ticker: "GOOGL", price: 175.2, change_percent: -0.3, direction: "down" },
];

const mockPrices: PriceMap = {
  AAPL: {
    ticker: "AAPL",
    price: 192.0,
    previous_price: 190.5,
    timestamp: Date.now() / 1000,
    change: 1.5,
    change_percent: 0.79,
    direction: "up",
  },
};

const mockSparklines: Record<string, SparklinePoint[]> = {
  AAPL: [
    { time: 1000, price: 190 },
    { time: 2000, price: 192 },
  ],
};

describe("WatchlistPanel", () => {
  const onSelectTicker = vi.fn();
  const onAddTicker = vi.fn().mockResolvedValue({ success: true, message: "Added" });
  const onRemoveTicker = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders watchlist rows for each ticker", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    expect(screen.getByTestId("watchlist-row-AAPL")).toBeTruthy();
    expect(screen.getByTestId("watchlist-row-GOOGL")).toBeTruthy();
  });

  it("displays live price from prices prop over watchlist entry price", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    // AAPL live price is $192.00 from mockPrices
    const priceCell = screen.getByTestId("price-AAPL");
    expect(priceCell.textContent).toContain("192");
  });

  it("calls onSelectTicker when a row is clicked", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    fireEvent.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(onSelectTicker).toHaveBeenCalledWith("AAPL");
  });

  it("calls onRemoveTicker when remove button is clicked", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    fireEvent.click(screen.getByTestId("watchlist-remove-AAPL"));
    expect(onRemoveTicker).toHaveBeenCalledWith("AAPL");
  });

  it("applies price-flash-up class when flash is up", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{ AAPL: "up" }}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    const priceCell = screen.getByTestId("price-AAPL");
    expect(priceCell.className).toContain("price-flash-up");
  });

  it("applies price-flash-down class when flash is down", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{ GOOGL: "down" }}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    const priceCell = screen.getByTestId("price-GOOGL");
    expect(priceCell.className).toContain("price-flash-down");
  });

  it("highlights selected ticker row", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker="AAPL"
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    const row = screen.getByTestId("watchlist-row-AAPL");
    // Check the row has selected styling (blue border) — jsdom converts hex to rgb
    const borderLeft = row.style.borderLeft;
    expect(borderLeft).toMatch(/2px solid (rgb\(32, 157, 215\)|#209dd7)/);
  });

  it("shows add ticker input and button", () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    expect(screen.getByTestId("watchlist-add-input")).toBeTruthy();
    expect(screen.getByTestId("watchlist-add-button")).toBeTruthy();
  });

  it("calls onAddTicker when form is submitted", async () => {
    render(
      <WatchlistPanel
        watchlist={mockWatchlist}
        prices={mockPrices}
        sparklines={mockSparklines}
        flashMap={{}}
        selectedTicker={null}
        onSelectTicker={onSelectTicker}
        onAddTicker={onAddTicker}
        onRemoveTicker={onRemoveTicker}
      />
    );

    const input = screen.getByTestId("watchlist-add-input");
    fireEvent.change(input, { target: { value: "TSLA" } });
    fireEvent.click(screen.getByTestId("watchlist-add-button"));

    expect(onAddTicker).toHaveBeenCalledWith("TSLA");
  });
});
