"use client";

// ────────────────────────────────────────────────────────────────────────────
// Watchlist hook — manages the list of tickers the user is watching
// ────────────────────────────────────────────────────────────────────────────
import { useState, useCallback, useEffect } from "react";
import { fetchWatchlist, addToWatchlist, removeFromWatchlist } from "@/lib/api";
import type { WatchlistEntry } from "@/lib/types";

export interface UseWatchlistResult {
  watchlist: WatchlistEntry[];
  loading: boolean;
  error: string | null;
  add: (ticker: string) => Promise<{ success: boolean; message: string }>;
  remove: (ticker: string) => Promise<{ success: boolean; message: string }>;
  refresh: () => Promise<void>;
}

export function useWatchlist(): UseWatchlistResult {
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchWatchlist();
      setWatchlist(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const add = useCallback(
    async (ticker: string): Promise<{ success: boolean; message: string }> => {
      try {
        await addToWatchlist(ticker);
        await refresh();
        return { success: true, message: `Added ${ticker.toUpperCase()}` };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to add ticker";
        return { success: false, message: msg };
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (ticker: string): Promise<{ success: boolean; message: string }> => {
      try {
        await removeFromWatchlist(ticker);
        setWatchlist((prev) => prev.filter((w) => w.ticker !== ticker.toUpperCase()));
        return { success: true, message: `Removed ${ticker.toUpperCase()}` };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to remove ticker";
        return { success: false, message: msg };
      }
    },
    []
  );

  return { watchlist, loading, error, add, remove, refresh };
}
