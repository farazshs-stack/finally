"use client";

import React, { useState } from "react";
import type { TradeRequest } from "@/lib/types";

interface TradeBarProps {
  onTrade: (req: TradeRequest) => Promise<{ success: boolean; message: string }>;
  defaultTicker?: string;
  cashBalance?: number;
}

export function TradeBar({ onTrade, defaultTicker, cashBalance }: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker ?? "");
  const [quantity, setQuantity] = useState("");
  const [status, setStatus] = useState<{ success: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(false);

  // Update ticker when selected ticker changes
  React.useEffect(() => {
    if (defaultTicker) setTicker(defaultTicker);
  }, [defaultTicker]);

  async function handleTrade(side: "buy" | "sell") {
    const t = ticker.trim().toUpperCase();
    const q = parseFloat(quantity);
    if (!t || isNaN(q) || q <= 0) {
      setStatus({ success: false, message: "Enter a valid ticker and quantity" });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const result = await onTrade({ ticker: t, quantity: q, side });
      setStatus(result);
      if (result.success) {
        setQuantity("");
      }
    } finally {
      setLoading(false);
      // Auto-clear after 4 seconds
      setTimeout(() => setStatus(null), 4000);
    }
  }

  return (
    <div
      style={{
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: "6px",
        padding: "10px 14px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
        <span style={{ color: "#8b949e", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", minWidth: "44px" }}>
          Trade
        </span>

        <input
          data-testid="trade-ticker-input"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="TICKER"
          maxLength={10}
          style={{
            width: "90px",
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: "4px",
            color: "#e6edf3",
            fontSize: "13px",
            padding: "6px 10px",
            outline: "none",
            fontFamily: "inherit",
            fontWeight: 700,
            letterSpacing: "0.05em",
          }}
        />

        <input
          data-testid="trade-quantity-input"
          type="number"
          min="0.0001"
          step="0.0001"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Shares"
          style={{
            width: "100px",
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: "4px",
            color: "#e6edf3",
            fontSize: "13px",
            padding: "6px 10px",
            outline: "none",
            fontFamily: "inherit",
          }}
        />

        <button
          data-testid="trade-buy-button"
          onClick={() => handleTrade("buy")}
          disabled={loading}
          style={{
            background: "#753991",
            border: "none",
            borderRadius: "4px",
            color: "#fff",
            fontSize: "13px",
            fontWeight: 700,
            padding: "6px 18px",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
            letterSpacing: "0.05em",
            fontFamily: "inherit",
          }}
        >
          BUY
        </button>

        <button
          data-testid="trade-sell-button"
          onClick={() => handleTrade("sell")}
          disabled={loading}
          style={{
            background: "#753991",
            border: "none",
            borderRadius: "4px",
            color: "#fff",
            fontSize: "13px",
            fontWeight: 700,
            padding: "6px 16px",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
            letterSpacing: "0.05em",
            fontFamily: "inherit",
          }}
        >
          SELL
        </button>

        {cashBalance != null && (
          <span style={{ color: "#6e7681", fontSize: "11px", marginLeft: "auto" }}>
            Cash:{" "}
            <span style={{ color: "#8b949e" }}>
              {cashBalance.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 })}
            </span>
          </span>
        )}
      </div>

      {status && (
        <div
          style={{
            marginTop: "6px",
            fontSize: "12px",
            color: status.success ? "#3fb950" : "#f85149",
          }}
        >
          {status.message}
        </div>
      )}
    </div>
  );
}
