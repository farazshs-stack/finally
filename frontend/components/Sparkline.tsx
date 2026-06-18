"use client";

import React, { useMemo } from "react";
import type { SparklinePoint } from "@/lib/types";

interface SparklineProps {
  data: SparklinePoint[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({ data, width = 80, height = 28, color }: SparklineProps) {
  const path = useMemo(() => {
    if (data.length < 2) return null;
    const prices = data.map((d) => d.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const xStep = width / (data.length - 1);

    const points = data.map((d, i) => {
      const x = i * xStep;
      const y = height - ((d.price - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return `M ${points.join(" L ")}`;
  }, [data, width, height]);

  const lineColor =
    color ??
    (data.length >= 2 && data[data.length - 1].price >= data[0].price ? "#3fb950" : "#f85149");

  if (!path) {
    return (
      <svg width={width} height={height} style={{ display: "block" }}>
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="#30363d"
          strokeWidth="1"
        />
      </svg>
    );
  }

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <path d={path} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
