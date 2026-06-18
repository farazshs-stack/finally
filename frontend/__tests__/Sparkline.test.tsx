import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Sparkline } from "@/components/Sparkline";
import type { SparklinePoint } from "@/lib/types";

describe("Sparkline", () => {
  it("renders an SVG element", () => {
    const data: SparklinePoint[] = [
      { time: 1000, price: 100 },
      { time: 2000, price: 105 },
      { time: 3000, price: 103 },
    ];
    const { container } = render(<Sparkline data={data} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("renders a flat line when data has fewer than 2 points", () => {
    const { container } = render(<Sparkline data={[]} />);
    const line = container.querySelector("line");
    expect(line).toBeTruthy();
  });

  it("uses green color when price trended up", () => {
    const data: SparklinePoint[] = [
      { time: 1000, price: 100 },
      { time: 2000, price: 110 },
    ];
    const { container } = render(<Sparkline data={data} />);
    const path = container.querySelector("path");
    expect(path?.getAttribute("stroke")).toBe("#3fb950");
  });

  it("uses red color when price trended down", () => {
    const data: SparklinePoint[] = [
      { time: 1000, price: 110 },
      { time: 2000, price: 100 },
    ];
    const { container } = render(<Sparkline data={data} />);
    const path = container.querySelector("path");
    expect(path?.getAttribute("stroke")).toBe("#f85149");
  });

  it("respects custom color prop", () => {
    const data: SparklinePoint[] = [
      { time: 1000, price: 100 },
      { time: 2000, price: 105 },
    ];
    const { container } = render(<Sparkline data={data} color="#ecad0a" />);
    const path = container.querySelector("path");
    expect(path?.getAttribute("stroke")).toBe("#ecad0a");
  });
});
