"use client";

// ────────────────────────────────────────────────────────────────────────────
// Portfolio heatmap — treemap using Recharts Treemap component
// Positions sized by market value, colored by unrealized P&L
// ────────────────────────────────────────────────────────────────────────────
import React from "react";
import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import type { Position, PriceMap } from "@/lib/types";

interface PortfolioHeatmapProps {
  positions: Position[];
  prices: PriceMap;
}

function pnlColor(pnlPct: number): string {
  if (pnlPct > 5) return "#196030";
  if (pnlPct > 2) return "#238636";
  if (pnlPct > 0) return "#2ea043";
  if (pnlPct > -2) return "#8b1a1a";
  if (pnlPct > -5) return "#b91c1c";
  return "#dc2626";
}

interface HeatmapEntry {
  name: string;
  size: number;
  pnlPct: number;
  pnl: number;
  price: number;
  [key: string]: unknown;
}

// Custom content renderer for the treemap cells
function CustomCell(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPct?: number;
  pnl?: number;
  price?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, pnlPct = 0, pnl = 0, price = 0 } = props;
  const bg = pnlColor(pnlPct);
  const sign = pnl >= 0 ? "+" : "";
  const showLabel = width > 40 && height > 30;
  const showDetail = width > 70 && height > 50;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={width - 2}
        height={height - 2}
        rx={4}
        fill={bg}
        stroke="#0d1117"
        strokeWidth={2}
      />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (showDetail ? 8 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#e6edf3"
            fontSize={Math.min(14, width / 4)}
            fontWeight={700}
          >
            {name}
          </text>
          {showDetail && (
            <>
              <text
                x={x + width / 2}
                y={y + height / 2 + 8}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={pnlPct >= 0 ? "#86efac" : "#fca5a5"}
                fontSize={Math.min(11, width / 5)}
              >
                {sign}{pnlPct.toFixed(2)}%
              </text>
              <text
                x={x + width / 2}
                y={y + height / 2 + 22}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#8b949e"
                fontSize={Math.min(10, width / 6)}
              >
                ${price.toFixed(2)}
              </text>
            </>
          )}
        </>
      )}
    </g>
  );
}

interface TooltipPayload {
  payload?: {
    name?: string;
    pnlPct?: number;
    pnl?: number;
    price?: number;
    size?: number;
  };
}

function HeatmapTooltip({ payload }: { payload?: TooltipPayload[] }) {
  if (!payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const sign = (d.pnl ?? 0) >= 0 ? "+" : "";
  return (
    <div
      style={{
        background: "#1c2128",
        border: "1px solid #30363d",
        borderRadius: "6px",
        padding: "8px 12px",
        fontSize: "12px",
        color: "#e6edf3",
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: "4px" }}>{d.name}</div>
      <div>Price: ${(d.price ?? 0).toFixed(2)}</div>
      <div style={{ color: (d.pnl ?? 0) >= 0 ? "#3fb950" : "#f85149" }}>
        P&L: {sign}${Math.abs(d.pnl ?? 0).toFixed(2)} ({sign}{(d.pnlPct ?? 0).toFixed(2)}%)
      </div>
      <div style={{ color: "#8b949e" }}>
        Value: ${(d.size ?? 0).toFixed(2)}
      </div>
    </div>
  );
}

export function PortfolioHeatmap({ positions, prices }: PortfolioHeatmapProps) {
  const data: HeatmapEntry[] = positions
    .map((pos) => {
      const livePrice = prices[pos.ticker]?.price ?? pos.current_price;
      const liveValue = pos.quantity * livePrice;
      const livePnl = liveValue - pos.quantity * pos.avg_cost;
      const livePnlPct = pos.avg_cost > 0 ? (livePnl / (pos.quantity * pos.avg_cost)) * 100 : 0;
      return {
        name: pos.ticker,
        size: Math.max(liveValue, 0.01),
        pnlPct: livePnlPct,
        pnl: livePnl,
        price: livePrice,
      };
    })
    .filter((d) => d.size > 0);

  return (
    <div
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
          Portfolio Heatmap
        </span>
      </div>
      <div style={{ flex: 1, padding: "4px" }}>
        {data.length === 0 ? (
          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6e7681",
              fontSize: "12px",
            }}
          >
            No positions yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              nameKey="name"
              aspectRatio={4 / 3}
              content={<CustomCell />}
            >
              <Tooltip content={<HeatmapTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
