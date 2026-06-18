"use client";

// ────────────────────────────────────────────────────────────────────────────
// Main ticker chart using lightweight-charts v5 (canvas-based)
// ────────────────────────────────────────────────────────────────────────────
import React, { useEffect, useRef, useState } from "react";
import type { SparklinePoint } from "@/lib/types";

interface MainChartProps {
  ticker: string | null;
  data: SparklinePoint[];
  currentPrice?: number;
}

export function MainChart({ ticker, data, currentPrice }: MainChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<{ chart: any; series: any } | null>(null);
  const [ready, setReady] = useState(false);

  // Dynamically import lightweight-charts (client only, ESM)
  useEffect(() => {
    let destroyed = false;

    async function init() {
      if (!containerRef.current) return;
      const lc = await import("lightweight-charts");
      if (destroyed || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const chart = lc.createChart(containerRef.current, {
        width: rect.width || 600,
        height: rect.height || 300,
        layout: {
          background: { color: "#161b22" },
          textColor: "#8b949e",
        },
        grid: {
          vertLines: { color: "#21262d" },
          horzLines: { color: "#21262d" },
        },
        crosshair: {
          mode: 1,
        },
        rightPriceScale: {
          borderColor: "#30363d",
          textColor: "#8b949e",
        },
        timeScale: {
          borderColor: "#30363d",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      // v5 API: addSeries(LineSeries, options)
      const series = chart.addSeries(lc.LineSeries, {
        color: "#209dd7",
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        priceLineVisible: true,
        priceLineColor: "#209dd7",
        priceLineStyle: 2,
        lastValueVisible: true,
      });

      chartRef.current = { chart, series };
      setReady(true);
    }

    init();

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        chartRef.current.chart.resize(rect.width, rect.height);
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      destroyed = true;
      ro.disconnect();
      if (chartRef.current) {
        chartRef.current.chart.remove();
        chartRef.current = null;
      }
    };
  }, []);

  // Feed data whenever it changes
  useEffect(() => {
    if (!ready || !chartRef.current) return;
    const { series, chart } = chartRef.current;

    if (data.length < 2) {
      series.setData([]);
      return;
    }

    // Deduplicate by second-level time (lightweight-charts requirement)
    const seen = new Set<number>();
    const lcData = data
      .map((p) => ({ time: Math.floor(p.time / 1000) as unknown as string, value: p.price }))
      .filter((p) => {
        const t = Number(p.time);
        if (seen.has(t)) return false;
        seen.add(t);
        return true;
      })
      .sort((a, b) => Number(a.time) - Number(b.time));

    series.setData(lcData);
    chart.timeScale().fitContent();
  }, [data, ready]);

  const noData = !ticker;

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
      {/* Chart header */}
      <div
        style={{
          padding: "8px 14px",
          borderBottom: "1px solid #30363d",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <span
          style={{
            color: ticker ? "#e6edf3" : "#6e7681",
            fontWeight: 700,
            fontSize: "16px",
          }}
        >
          {ticker ?? "Select a ticker"}
        </span>
        {currentPrice != null && ticker && (
          <span style={{ color: "#209dd7", fontWeight: 600, fontSize: "14px" }}>
            {currentPrice.toLocaleString("en-US", {
              style: "currency",
              currency: "USD",
              minimumFractionDigits: 2,
            })}
          </span>
        )}
        <span style={{ marginLeft: "auto", color: "#6e7681", fontSize: "10px" }}>
          Since page load
        </span>
      </div>

      {/* Chart container */}
      <div style={{ flex: 1, position: "relative" }}>
        {noData && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6e7681",
              fontSize: "13px",
            }}
          >
            Click a ticker in the watchlist to view its chart
          </div>
        )}
        <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      </div>
    </div>
  );
}
