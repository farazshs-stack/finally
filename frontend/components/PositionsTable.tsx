"use client";

import React from "react";
import type { Position, PriceMap } from "@/lib/types";

interface PositionsTableProps {
  positions: Position[];
  prices: PriceMap;
}

function fmt(n: number, digits = 2): string {
  return n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtUsd(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export function PositionsTable({ positions, prices }: PositionsTableProps) {
  return (
    <div
      data-testid="positions-table"
      style={{
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: "6px",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <div
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid #30363d",
        }}
      >
        <span style={{ color: "#8b949e", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Positions
        </span>
      </div>
      <div style={{ flex: 1, overflowY: "auto" }}>
        {positions.length === 0 ? (
          <div
            style={{
              padding: "16px",
              color: "#6e7681",
              textAlign: "center",
              fontSize: "12px",
            }}
          >
            No positions — buy some shares to get started
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Qty</th>
                <th>Avg Cost</th>
                <th>Price</th>
                <th>Value</th>
                <th>P&L</th>
                <th>%</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => {
                const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
                const liveValue = pos.quantity * livePrice;
                const livePnl = liveValue - pos.quantity * pos.avg_cost;
                const livePnlPct =
                  pos.avg_cost > 0 ? (livePnl / (pos.quantity * pos.avg_cost)) * 100 : 0;
                const pnlColor = livePnl >= 0 ? "#3fb950" : "#f85149";

                return (
                  <tr key={pos.ticker}>
                    <td>
                      <span style={{ color: "#ecad0a", fontWeight: 700 }}>{pos.ticker}</span>
                    </td>
                    <td>{fmt(pos.quantity, pos.quantity % 1 === 0 ? 0 : 4)}</td>
                    <td>{fmtUsd(pos.avg_cost)}</td>
                    <td style={{ color: "#e6edf3" }}>{fmtUsd(livePrice)}</td>
                    <td>{fmtUsd(liveValue)}</td>
                    <td style={{ color: pnlColor }}>
                      {livePnl >= 0 ? "+" : ""}
                      {fmtUsd(livePnl)}
                    </td>
                    <td style={{ color: pnlColor }}>
                      {livePnlPct >= 0 ? "+" : ""}
                      {fmt(livePnlPct)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
