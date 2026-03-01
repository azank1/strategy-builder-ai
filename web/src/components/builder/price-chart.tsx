"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import { cn } from "@/lib/utils";
import type { PricePoint } from "@/lib/api";

/* ───────────────────────────────────────────────────────────────────────────
 * PriceChart — OHLC area chart with regime bands and ISP zone overlays
 *
 * Supports:
 *  - Regime color bands (background shading per regime period)
 *  - ISP highlight zones (user-drawn signal periods)
 *  - Reference price lines (e.g. moving averages)
 *  - Click handler for ISP point selection
 * ─────────────────────────────────────────────────────────────────────────── */

export interface RegimeBand {
  start: string; // ISO date
  end: string;
  label: string;
  color: string; // tailwind-style hex
}

export interface ISPZone {
  start: string;
  end: string;
  signal: "buy" | "sell" | "neutral";
}

export interface ReferencePriceLine {
  label: string;
  value: number;
  color: string;
}

interface Props {
  data: PricePoint[];
  regimeBands?: RegimeBand[];
  ispZones?: ISPZone[];
  referenceLines?: ReferencePriceLine[];
  height?: number;
  onChartClick?: (date: string, price: number) => void;
  showVolume?: boolean;
}

const ISP_COLORS: Record<string, { fill: string; opacity: number }> = {
  buy: { fill: "#10b981", opacity: 0.12 },
  sell: { fill: "#ef4444", opacity: 0.12 },
  neutral: { fill: "#a1a1aa", opacity: 0.06 },
};

const REGIME_OPACITY = 0.08;

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatPrice(v: number) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(2);
}

export function PriceChart({
  data,
  regimeBands = [],
  ispZones = [],
  referenceLines = [],
  height = 320,
  onChartClick,
  showVolume = false,
}: Props) {
  // Transform for recharts — use close price as primary series
  const chartData = useMemo(
    () =>
      data.map((p) => ({
        date: p.date,
        close: p.close,
        high: p.high,
        low: p.low,
        volume: p.volume,
      })),
    [data]
  );

  const [minPrice, maxPrice] = useMemo(() => {
    if (chartData.length === 0) return [0, 1];
    const lows = chartData.map((d) => d.low ?? d.close);
    const highs = chartData.map((d) => d.high ?? d.close);
    const min = Math.min(...lows);
    const max = Math.max(...highs);
    const pad = (max - min) * 0.05;
    return [min - pad, max + pad];
  }, [chartData]);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/50 text-sm text-zinc-500"
        style={{ height }}
      >
        No price data available
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl border border-zinc-800 bg-zinc-900/50 p-2")}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={chartData}
          onClick={(e: unknown) => {
            const event = e as { activePayload?: { payload: { date: string; close: number } }[] };
            if (event?.activePayload?.[0]) {
              const payload = event.activePayload[0].payload;
              onChartClick?.(payload.date, payload.close);
            }
          }}
        >
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>

          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            minTickGap={50}
          />
          <YAxis
            domain={[minPrice, maxPrice]}
            tickFormatter={formatPrice}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "8px",
              fontSize: 12,
            }}
            labelFormatter={(label) => formatDate(String(label))}
            formatter={(value) => [`$${Number(value).toLocaleString()}`, "Close"]}
          />

          {/* Regime background bands */}
          {regimeBands.map((band, i) => (
            <ReferenceArea
              key={`regime-${i}`}
              x1={band.start}
              x2={band.end}
              fill={band.color}
              fillOpacity={REGIME_OPACITY}
              strokeOpacity={0}
            />
          ))}

          {/* ISP zones */}
          {ispZones.map((zone, i) => {
            const style = ISP_COLORS[zone.signal];
            return (
              <ReferenceArea
                key={`isp-${i}`}
                x1={zone.start}
                x2={zone.end}
                fill={style.fill}
                fillOpacity={style.opacity}
                strokeOpacity={0}
              />
            );
          })}

          {/* Reference price lines */}
          {referenceLines.map((line, i) => (
            <ReferenceLine
              key={`ref-${i}`}
              y={line.value}
              stroke={line.color}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
              label={{
                value: line.label,
                fill: line.color,
                fontSize: 10,
                position: "right",
              }}
            />
          ))}

          <Area
            type="monotone"
            dataKey="close"
            stroke="#3b82f6"
            strokeWidth={1.5}
            fill="url(#priceGradient)"
            dot={false}
            activeDot={{ r: 4, fill: "#3b82f6", stroke: "#fff", strokeWidth: 1 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
