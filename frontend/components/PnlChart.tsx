"use client";

// ────────────────────────────────────────────────────────────────────────────
// P&L chart — line chart of portfolio total value over time
// Data from GET /api/portfolio/history
// ────────────────────────────────────────────────────────────────────────────
import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchPortfolioHistory } from "@/lib/api";
import type { PortfolioSnapshot } from "@/lib/types";

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function fmtUsd(v: number): string {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#1c2128",
        border: "1px solid #30363d",
        borderRadius: "6px",
        padding: "8px 12px",
        fontSize: "12px",
      }}
    >
      <div style={{ color: "#8b949e" }}>{label}</div>
      <div style={{ color: "#209dd7", fontWeight: 600 }}>{fmtUsd(payload[0].value)}</div>
    </div>
  );
}

interface PnlChartProps {
  refreshTrigger?: number;
}

export function PnlChart({ refreshTrigger }: PnlChartProps) {
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchPortfolioHistory()
      .then((data) => {
        setSnapshots(data);
      })
      .catch(() => {
        // silently fail
      })
      .finally(() => setLoading(false));
  }, [refreshTrigger]);

  const chartData = snapshots.map((s) => ({
    time: fmtTime(s.recorded_at),
    value: s.total_value,
  }));

  const hasData = chartData.length > 0;
  const minVal = hasData ? Math.min(...chartData.map((d) => d.value)) : 0;
  const maxVal = hasData ? Math.max(...chartData.map((d) => d.value)) : 12000;
  const padding = (maxVal - minVal) * 0.1 || 500;

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
          Portfolio Value
        </span>
      </div>
      <div style={{ flex: 1, padding: "8px 0 4px" }}>
        {loading && (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#6e7681", fontSize: "12px" }}>
            Loading…
          </div>
        )}
        {!loading && !hasData && (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#6e7681", fontSize: "12px" }}>
            No history yet — make a trade to record a snapshot
          </div>
        )}
        {!loading && hasData && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="#21262d" strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                tick={{ fill: "#6e7681", fontSize: 10 }}
                axisLine={{ stroke: "#30363d" }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[minVal - padding, maxVal + padding]}
                tick={{ fill: "#6e7681", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
                width={48}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#209dd7"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#209dd7" }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
