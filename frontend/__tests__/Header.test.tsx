import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "@/components/Header";

describe("Header", () => {
  it("renders total value with data-testid", () => {
    render(<Header totalValue={12345.67} cashBalance={5000} status="connected" />);
    const totalEl = screen.getByTestId("total-value");
    expect(totalEl.textContent).toContain("12,345");
  });

  it("renders cash balance with data-testid", () => {
    render(<Header totalValue={12000} cashBalance={3500.25} status="connected" />);
    const cashEl = screen.getByTestId("cash-balance");
    expect(cashEl.textContent).toContain("3,500");
  });

  it("renders connection dot with correct status", () => {
    render(<Header totalValue={10000} cashBalance={5000} status="connected" />);
    const dot = screen.getByTestId("connection-dot");
    expect(dot.getAttribute("data-status")).toBe("connected");
  });

  it("shows reconnecting status on connection dot", () => {
    render(<Header totalValue={10000} cashBalance={5000} status="reconnecting" />);
    const dot = screen.getByTestId("connection-dot");
    expect(dot.getAttribute("data-status")).toBe("reconnecting");
  });

  it("shows disconnected status on connection dot", () => {
    render(<Header totalValue={10000} cashBalance={5000} status="disconnected" />);
    const dot = screen.getByTestId("connection-dot");
    expect(dot.getAttribute("data-status")).toBe("disconnected");
  });

  it("renders brand name", () => {
    render(<Header totalValue={10000} cashBalance={5000} status="connected" />);
    expect(screen.getByText("FIN")).toBeTruthy();
    expect(screen.getByText("ALLY")).toBeTruthy();
  });
});
