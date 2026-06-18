"use client";

import React, { useState } from "react";
import { Sparkline } from "./Sparkline";
import type { WatchlistEntry, PriceMap, SparklinePoint } from "@/lib/types";

interface WatchlistPanelProps {
  watchlist: WatchlistEntry[];
  prices: PriceMap;
  sparklines: Record<string, SparklinePoint[]>;
  flashMap: Record<string, "up" | "down">;
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
  onAddTicker: (ticker: string) => void;
  onRemoveTicker: (ticker: string) => void;
  loading?: boolean;
}

function fmtPrice(p: number): string {
  return p.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function fmtPct(p: number): string {
  const sign = p >= 0 ? "+" : "";
  return `${sign}${p.toFixed(2)}%`;
}

export function WatchlistPanel({
  watchlist,
  prices,
  sparklines,
  flashMap,
  selectedTicker,
  onSelectTicker,
  onAddTicker,
  onRemoveTicker,
  loading,
}: WatchlistPanelProps) {
  const [newTicker, setNewTicker] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    setAddError(null);
    try {
      await onAddTicker(t);
      setNewTicker("");
    } catch {
      setAddError("Failed to add ticker");
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: "6px",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #30363d",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#8b949e", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Watchlist
        </span>
      </div>

      {/* Add ticker form */}
      <form
        onSubmit={handleAdd}
        style={{ padding: "8px 10px", borderBottom: "1px solid #30363d", display: "flex", gap: "6px" }}
      >
        <input
          data-testid="watchlist-add-input"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
          placeholder="Add ticker…"
          style={{
            flex: 1,
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: "4px",
            color: "#e6edf3",
            fontSize: "12px",
            padding: "4px 8px",
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <button
          data-testid="watchlist-add-button"
          type="submit"
          style={{
            background: "#209dd7",
            border: "none",
            borderRadius: "4px",
            color: "#fff",
            fontSize: "12px",
            padding: "4px 10px",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          +
        </button>
      </form>
      {addError && (
        <div style={{ padding: "4px 12px", color: "#f85149", fontSize: "11px" }}>{addError}</div>
      )}

      {/* Column headers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 70px 60px 80px 20px",
          padding: "4px 10px",
          gap: "4px",
        }}
      >
        <span style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase" }}>Symbol</span>
        <span style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase", textAlign: "right" }}>Price</span>
        <span style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase", textAlign: "right" }}>Chg%</span>
        <span style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase", textAlign: "center" }}>Chart</span>
        <span />
      </div>

      {/* Ticker rows */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {loading && watchlist.length === 0 && (
          <div style={{ padding: "16px", color: "#6e7681", textAlign: "center", fontSize: "12px" }}>
            Loading…
          </div>
        )}
        {watchlist.map((entry) => {
          const live = prices[entry.ticker];
          const price = live?.price ?? entry.price ?? 0;
          const changePct = live?.change_percent ?? entry.change_percent ?? 0;
          const direction = live?.direction ?? entry.direction ?? "flat";
          const flash = flashMap[entry.ticker];
          const sparks = sparklines[entry.ticker] ?? [];
          const isSelected = selectedTicker === entry.ticker;

          return (
            <div
              key={entry.ticker}
              data-testid={`watchlist-row-${entry.ticker}`}
              onClick={() => onSelectTicker(entry.ticker)}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 70px 60px 80px 20px",
                padding: "5px 10px",
                gap: "4px",
                alignItems: "center",
                cursor: "pointer",
                borderBottom: "1px solid rgba(48,54,61,0.5)",
                background: isSelected
                  ? "rgba(32, 157, 215, 0.08)"
                  : "transparent",
                borderLeft: isSelected ? "2px solid #209dd7" : "2px solid transparent",
                transition: "background 0.15s",
              }}
            >
              {/* Ticker */}
              <span style={{ color: "#e6edf3", fontWeight: 700, fontSize: "13px" }}>
                {entry.ticker}
              </span>

              {/* Price with flash */}
              <span
                data-testid={`price-${entry.ticker}`}
                className={
                  flash === "up"
                    ? "price-flash-up"
                    : flash === "down"
                    ? "price-flash-down"
                    : ""
                }
                style={{
                  textAlign: "right",
                  color: "#e6edf3",
                  fontSize: "12px",
                  fontWeight: 600,
                  borderRadius: "3px",
                  padding: "1px 3px",
                }}
              >
                {fmtPrice(price)}
              </span>

              {/* Change % */}
              <span
                style={{
                  textAlign: "right",
                  color: direction === "up" ? "#3fb950" : direction === "down" ? "#f85149" : "#8b949e",
                  fontSize: "11px",
                }}
              >
                {fmtPct(changePct)}
              </span>

              {/* Sparkline */}
              <div style={{ display: "flex", justifyContent: "center" }}>
                <Sparkline data={sparks} width={72} height={24} />
              </div>

              {/* Remove button */}
              <button
                data-testid={`watchlist-remove-${entry.ticker}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveTicker(entry.ticker);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#6e7681",
                  cursor: "pointer",
                  fontSize: "14px",
                  lineHeight: 1,
                  padding: "0",
                }}
                title="Remove"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
