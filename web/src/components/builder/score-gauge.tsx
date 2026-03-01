"use client";

import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * ScoreGauge — a semi-circular or linear gauge for z-scores / ratios
 *
 * Renders a horizontal bar gauge with colored zones and a pointer.
 * Works for z-scores (range -4 to +4) and trend ratios (-1 to +1).
 * ─────────────────────────────────────────────────────────────────────────── */

interface ScoreGaugeProps {
  value: number;
  min?: number;
  max?: number;
  label: string;
  subLabel?: string;
  zones?: { from: number; to: number; color: string; label: string }[];
  size?: "sm" | "md" | "lg";
}

const DEFAULT_ZONES = [
  { from: -4, to: -2, color: "bg-emerald-600", label: "Extreme Buy" },
  { from: -2, to: -1, color: "bg-emerald-500/60", label: "Buy" },
  { from: -1, to: 1, color: "bg-zinc-600", label: "Fair" },
  { from: 1, to: 2, color: "bg-red-500/60", label: "Sell" },
  { from: 2, to: 4, color: "bg-red-600", label: "Extreme Sell" },
];

export function ScoreGauge({
  value,
  min = -4,
  max = 4,
  label,
  subLabel,
  zones = DEFAULT_ZONES,
  size = "md",
}: ScoreGaugeProps) {
  const range = max - min;
  const pct = Math.max(0, Math.min(100, ((value - min) / range) * 100));

  const heights = { sm: "h-3", md: "h-4", lg: "h-6" };
  const textSizes = { sm: "text-lg", md: "text-2xl", lg: "text-3xl" };

  // Determine label color from zone
  const activeZone = zones.find((z) => value >= z.from && value < z.to) ?? zones[zones.length - 1];

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-zinc-400">{label}</span>
        <div className="flex items-baseline gap-2">
          <span className={cn("font-bold tabular-nums", textSizes[size])}>
            {value.toFixed(2)}
          </span>
          {subLabel && (
            <span className="text-xs text-zinc-500">{subLabel}</span>
          )}
        </div>
      </div>

      {/* Bar */}
      <div className={cn("relative w-full rounded-full overflow-hidden", heights[size])}>
        <div className="absolute inset-0 flex">
          {zones.map((zone) => {
            const width = ((zone.to - zone.from) / range) * 100;
            return (
              <div
                key={`${zone.from}-${zone.to}`}
                className={cn(zone.color)}
                style={{ width: `${width}%` }}
              />
            );
          })}
        </div>
        {/* Pointer */}
        <div
          className="absolute top-0 h-full w-0.5 bg-white shadow-[0_0_6px_rgba(255,255,255,0.8)] transition-all duration-300"
          style={{ left: `${pct}%` }}
        />
      </div>

      {/* Zone label */}
      <p className="text-xs text-zinc-500">
        {activeZone?.label}
      </p>
    </div>
  );
}

/* ─── Preset for trend ratios ─────────────────────────────────────────────── */

const TREND_ZONES = [
  { from: -1, to: -0.6, color: "bg-red-600", label: "Strong Downtrend" },
  { from: -0.6, to: -0.2, color: "bg-red-500/60", label: "Moderate Downtrend" },
  { from: -0.2, to: 0.2, color: "bg-zinc-600", label: "Neutral" },
  { from: 0.2, to: 0.6, color: "bg-emerald-500/60", label: "Moderate Uptrend" },
  { from: 0.6, to: 1, color: "bg-emerald-600", label: "Strong Uptrend" },
];

export function TrendGauge({
  value,
  label = "Trend Ratio",
  subLabel,
}: {
  value: number;
  label?: string;
  subLabel?: string;
}) {
  return (
    <ScoreGauge
      value={value}
      min={-1}
      max={1}
      label={label}
      subLabel={subLabel}
      zones={TREND_ZONES}
    />
  );
}
