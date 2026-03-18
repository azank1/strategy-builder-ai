"use client";

import { useMemo } from "react";
import {
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Line,
  ComposedChart,
} from "recharts";
import type { EquityPoint } from "./engine";

/* ───────────────────────────────────────────────────────────────────────────
 * EquityChart — Real-time equity curve with buy-and-hold reference line.
 * Updates instantly as the user adds/removes trades.
 * ─────────────────────────────────────────────────────────────────────────── */

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatValue(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

interface Props {
  equityCurve: EquityPoint[];
  initialCapital: number;
}

export function EquityChart({ equityCurve, initialCapital }: Props) {
  const [minEquity, maxEquity] = useMemo(() => {
    if (equityCurve.length === 0) return [0, initialCapital * 2];
    const values = equityCurve.map((e) => e.equity);
    const bhValues = equityCurve.map((e) => e.buyAndHold);
    const all = [...values, ...bhValues, initialCapital];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.08 || initialCapital * 0.05;
    return [min - pad, max + pad];
  }, [equityCurve, initialCapital]);

  if (equityCurve.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-xs text-zinc-600">
        Place trades on the chart above to see your equity curve
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={equityCurve}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fill: "#52525b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          minTickGap={60}
        />
        <YAxis
          domain={[minEquity, maxEquity]}
          tickFormatter={formatValue}
          tick={{ fill: "#52525b", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={65}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#18181b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelFormatter={(label) => formatDate(String(label))}
          formatter={(value, name) => [
            formatValue(Number(value)),
            name === "equity" ? "Strategy" : "Buy & Hold",
          ]}
        />

        {/* Initial capital reference */}
        <ReferenceLine
          y={initialCapital}
          stroke="#52525b"
          strokeDasharray="4 4"
          strokeWidth={1}
        />

        {/* Buy-and-hold benchmark */}
        <Line
          type="monotone"
          dataKey="buyAndHold"
          stroke="#52525b"
          strokeWidth={1}
          strokeDasharray="3 3"
          dot={false}
          isAnimationActive={false}
        />

        {/* Strategy equity */}
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#10b981"
          strokeWidth={2}
          fill="url(#equityGrad)"
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
