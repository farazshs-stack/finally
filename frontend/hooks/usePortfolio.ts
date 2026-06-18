"use client";

// ────────────────────────────────────────────────────────────────────────────
// Portfolio data hook — fetches positions + cash, re-fetches after trades
// ────────────────────────────────────────────────────────────────────────────
import { useState, useCallback, useEffect } from "react";
import { fetchPortfolio, executeTrade } from "@/lib/api";
import type { PortfolioResponse, Position, TradeRequest } from "@/lib/types";

export interface UsePortfolioResult {
  portfolio: PortfolioResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  trade: (req: TradeRequest) => Promise<{ success: boolean; message: string }>;
}

export function usePortfolio(): UsePortfolioResult {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchPortfolio();
      setPortfolio(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const trade = useCallback(
    async (req: TradeRequest): Promise<{ success: boolean; message: string }> => {
      try {
        const result = await executeTrade(req);
        if (result.success !== false) {
          await refresh();
        }
        return { success: result.success !== false, message: result.message ?? "Trade executed" };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Trade failed";
        return { success: false, message: msg };
      }
    },
    [refresh]
  );

  return { portfolio, loading, error, refresh, trade };
}

// ── Compute live total value from SSE prices + positions ──────────────────
export function computeLiveTotal(
  positions: Position[],
  prices: Record<string, { price: number }>,
  cashBalance: number
): number {
  const positionsValue = positions.reduce((sum, pos) => {
    const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
    return sum + pos.quantity * livePrice;
  }, 0);
  return cashBalance + positionsValue;
}
