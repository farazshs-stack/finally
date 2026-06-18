"use client";

// ────────────────────────────────────────────────────────────────────────────
// SSE price stream hook
// Connects to GET /api/stream/prices, maintains live price map + sparklines,
// and tracks connection status for the header dot.
// ────────────────────────────────────────────────────────────────────────────
import { useEffect, useRef, useState, useCallback } from "react";
import type { PriceMap, SparklinePoint } from "@/lib/types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

const MAX_SPARKLINE_POINTS = 120; // ~60 seconds at 500 ms intervals

export interface PriceStreamState {
  prices: PriceMap;
  sparklines: Record<string, SparklinePoint[]>;
  status: ConnectionStatus;
  flashMap: Record<string, "up" | "down">;
}

export function usePriceStream(): PriceStreamState {
  const [prices, setPrices] = useState<PriceMap>({});
  const [sparklines, setSparklines] = useState<Record<string, SparklinePoint[]>>({});
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [flashMap, setFlashMap] = useState<Record<string, "up" | "down">>({});

  // We use a ref to hold flash-timeout IDs so we can clear them
  const flashTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const triggerFlash = useCallback((ticker: string, dir: "up" | "down") => {
    // Clear any existing timer for this ticker
    if (flashTimers.current[ticker]) {
      clearTimeout(flashTimers.current[ticker]);
    }
    setFlashMap((prev) => ({ ...prev, [ticker]: dir }));
    flashTimers.current[ticker] = setTimeout(() => {
      setFlashMap((prev) => {
        const next = { ...prev };
        delete next[ticker];
        return next;
      });
    }, 550);
  }, []);

  useEffect(() => {
    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let destroyed = false;

    function connect() {
      if (destroyed) return;
      setStatus("reconnecting");

      es = new EventSource("/api/stream/prices");

      es.onopen = () => {
        if (!destroyed) setStatus("connected");
      };

      es.onmessage = (event) => {
        if (destroyed) return;
        try {
          const data: Record<string, {
            ticker: string;
            price: number;
            previous_price: number;
            timestamp: number;
            change: number;
            change_percent: number;
            direction: "up" | "down" | "flat";
          }> = JSON.parse(event.data);

          setPrices((prev) => ({ ...prev, ...data }));

          // Update sparklines
          setSparklines((prev) => {
            const next = { ...prev };
            const now = Date.now();
            for (const [ticker, update] of Object.entries(data)) {
              const existing = next[ticker] ?? [];
              const point: SparklinePoint = { time: update.timestamp * 1000 || now, price: update.price };
              const updated = [...existing, point];
              next[ticker] = updated.slice(-MAX_SPARKLINE_POINTS);
            }
            return next;
          });

          // Trigger flash for each updated ticker
          for (const [ticker, update] of Object.entries(data)) {
            if (update.direction !== "flat") {
              triggerFlash(ticker, update.direction as "up" | "down");
            }
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        if (destroyed) return;
        setStatus("reconnecting");
        es?.close();
        es = null;
        // EventSource retries automatically, but we'll manage reconnect ourselves
        // to show status accurately
        retryTimeout = setTimeout(connect, 2000);
      };
    }

    connect();

    return () => {
      destroyed = true;
      if (retryTimeout) clearTimeout(retryTimeout);
      if (es) es.close();
      // Clear all flash timers
      for (const id of Object.values(flashTimers.current)) {
        clearTimeout(id);
      }
    };
  }, [triggerFlash]);

  return { prices, sparklines, status, flashMap };
}
