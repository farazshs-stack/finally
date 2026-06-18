"use client";

import React from "react";
import type { ConnectionStatus } from "@/hooks/usePriceStream";

interface HeaderProps {
  totalValue: number;
  cashBalance: number;
  status: ConnectionStatus;
}

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: "#3fb950",
  reconnecting: "#ecad0a",
  disconnected: "#f85149",
};

const STATUS_LABELS: Record<ConnectionStatus, string> = {
  connected: "LIVE",
  reconnecting: "RECONNECTING",
  disconnected: "DISCONNECTED",
};

function fmt(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export function Header({ totalValue, cashBalance, status }: HeaderProps) {
  return (
    <header
      style={{
        background: "#161b22",
        borderBottom: "1px solid #30363d",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "48px",
        flexShrink: 0,
      }}
    >
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span
          style={{
            color: "#ecad0a",
            fontWeight: 700,
            fontSize: "16px",
            letterSpacing: "0.1em",
          }}
        >
          FIN<span style={{ color: "#209dd7" }}>ALLY</span>
        </span>
        <span style={{ color: "#30363d", fontSize: "14px" }}>|</span>
        <span style={{ color: "#8b949e", fontSize: "11px" }}>AI Trading Workstation</span>
      </div>

      {/* Center: portfolio value */}
      <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Portfolio Value
          </div>
          <div
            data-testid="total-value"
            style={{ color: "#e6edf3", fontSize: "18px", fontWeight: 700, letterSpacing: "0.02em" }}
          >
            {fmt(totalValue)}
          </div>
        </div>

        <div style={{ width: "1px", height: "32px", background: "#30363d" }} />

        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#6e7681", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Cash
          </div>
          <div
            data-testid="cash-balance"
            style={{ color: "#8b949e", fontSize: "14px", fontWeight: 600 }}
          >
            {fmt(cashBalance)}
          </div>
        </div>
      </div>

      {/* Connection status */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div
          data-testid="connection-dot"
          data-status={status}
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: STATUS_COLORS[status],
            boxShadow: status === "connected" ? `0 0 6px ${STATUS_COLORS[status]}` : "none",
            transition: "background-color 0.3s ease",
          }}
        />
        <span
          style={{
            color: STATUS_COLORS[status],
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.08em",
          }}
        >
          {STATUS_LABELS[status]}
        </span>
      </div>
    </header>
  );
}
