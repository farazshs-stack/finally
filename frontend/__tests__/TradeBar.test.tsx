import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TradeBar } from "@/components/TradeBar";

describe("TradeBar", () => {
  const mockOnTrade = vi.fn().mockResolvedValue({ success: true, message: "Trade executed" });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders ticker and quantity inputs", () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    expect(screen.getByTestId("trade-ticker-input")).toBeTruthy();
    expect(screen.getByTestId("trade-quantity-input")).toBeTruthy();
  });

  it("renders buy and sell buttons", () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    expect(screen.getByTestId("trade-buy-button")).toBeTruthy();
    expect(screen.getByTestId("trade-sell-button")).toBeTruthy();
  });

  it("calls onTrade with buy side when BUY is clicked", async () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    fireEvent.change(screen.getByTestId("trade-ticker-input"), { target: { value: "AAPL" } });
    fireEvent.change(screen.getByTestId("trade-quantity-input"), { target: { value: "5" } });
    fireEvent.click(screen.getByTestId("trade-buy-button"));

    await vi.waitFor(() => {
      expect(mockOnTrade).toHaveBeenCalledWith({ ticker: "AAPL", quantity: 5, side: "buy" });
    });
  });

  it("calls onTrade with sell side when SELL is clicked", async () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    fireEvent.change(screen.getByTestId("trade-ticker-input"), { target: { value: "TSLA" } });
    fireEvent.change(screen.getByTestId("trade-quantity-input"), { target: { value: "3" } });
    fireEvent.click(screen.getByTestId("trade-sell-button"));

    await vi.waitFor(() => {
      expect(mockOnTrade).toHaveBeenCalledWith({ ticker: "TSLA", quantity: 3, side: "sell" });
    });
  });

  it("shows error when ticker is empty", () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    fireEvent.change(screen.getByTestId("trade-quantity-input"), { target: { value: "5" } });
    fireEvent.click(screen.getByTestId("trade-buy-button"));
    expect(mockOnTrade).not.toHaveBeenCalled();
    expect(screen.getByText(/Enter a valid/)).toBeTruthy();
  });

  it("shows error when quantity is invalid", () => {
    render(<TradeBar onTrade={mockOnTrade} />);
    fireEvent.change(screen.getByTestId("trade-ticker-input"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByTestId("trade-buy-button"));
    expect(mockOnTrade).not.toHaveBeenCalled();
    expect(screen.getByText(/Enter a valid/)).toBeTruthy();
  });

  it("pre-fills ticker from defaultTicker prop", () => {
    render(<TradeBar onTrade={mockOnTrade} defaultTicker="NVDA" />);
    const input = screen.getByTestId("trade-ticker-input") as HTMLInputElement;
    expect(input.value).toBe("NVDA");
  });

  it("displays cash balance when provided", () => {
    render(<TradeBar onTrade={mockOnTrade} cashBalance={5000} />);
    expect(screen.getByText(/5,000/)).toBeTruthy();
  });
});
