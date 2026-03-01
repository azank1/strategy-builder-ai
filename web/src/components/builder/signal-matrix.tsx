"use client";

import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * SignalMatrix — the 7-cell valuation × trend allocation grid
 *
 * Rows: Valuation (Extreme Buy → Extreme Sell)
 * Columns: Trend (Uptrend / Neutral / Downtrend)
 * Each cell shows the resulting allocation % + signal label.
 * The active cell is highlighted based on current scores.
 * ─────────────────────────────────────────────────────────────────────────── */

interface Props {
  /** Current valuation signal: "strongest_buy" | "buy" | "hold" | "sell" | "strongest_sell" */
  valuationSignal?: string;
  /** Current trend signal: "uptrend" | "neutral" | "downtrend" */
  trendSignal?: string;
  /** Override allocations — keys like "strongest_buy:uptrend" → 1.0 */
  allocations?: Record<string, number>;
}

const VAL_ROWS = [
  { key: "strongest_buy", label: "Strong Buy", short: "SB" },
  { key: "buy", label: "Buy", short: "B" },
  { key: "hold", label: "Hold", short: "H" },
  { key: "sell", label: "Sell", short: "S" },
  { key: "strongest_sell", label: "Strong Sell", short: "SS" },
] as const;

const TREND_COLS = [
  { key: "uptrend", label: "Uptrend", short: "▲" },
  { key: "neutral", label: "Neutral", short: "—" },
  { key: "downtrend", label: "Downtrend", short: "▼" },
] as const;

// Default allocation map from composite.py logic
const DEFAULT_ALLOC: Record<string, number> = {
  "strongest_buy:uptrend": 1.0,
  "strongest_buy:neutral": 0.85,
  "strongest_buy:downtrend": 0.7,
  "buy:uptrend": 0.85,
  "buy:neutral": 0.7,
  "buy:downtrend": 0.55,
  "hold:uptrend": 0.5,
  "hold:neutral": 0.3,
  "hold:downtrend": 0.15,
  "sell:uptrend": 0.35,
  "sell:neutral": 0.2,
  "sell:downtrend": 0.05,
  "strongest_sell:uptrend": 0.15,
  "strongest_sell:neutral": 0.05,
  "strongest_sell:downtrend": 0.0,
};

function allocColor(pct: number): string {
  if (pct >= 0.8) return "bg-emerald-500/30 text-emerald-300";
  if (pct >= 0.6) return "bg-emerald-500/15 text-emerald-400";
  if (pct >= 0.4) return "bg-blue-500/15 text-blue-400";
  if (pct >= 0.2) return "bg-amber-500/15 text-amber-400";
  return "bg-red-500/20 text-red-400";
}

export function SignalMatrix({ valuationSignal, trendSignal, allocations }: Props) {
  const alloc = { ...DEFAULT_ALLOC, ...allocations };
  const activeKey = valuationSignal && trendSignal ? `${valuationSignal}:${trendSignal}` : null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="p-2 text-[10px] text-zinc-500 font-medium text-left">
              Valuation \ Trend
            </th>
            {TREND_COLS.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "p-2 text-xs font-medium text-center",
                  trendSignal === col.key ? "text-blue-400" : "text-zinc-500"
                )}
              >
                <span className="mr-1">{col.short}</span>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {VAL_ROWS.map((row) => (
            <tr key={row.key}>
              <td
                className={cn(
                  "p-2 text-xs font-medium whitespace-nowrap",
                  valuationSignal === row.key ? "text-blue-400" : "text-zinc-500"
                )}
              >
                <span className="mr-1.5 font-mono text-[10px] text-zinc-600">{row.short}</span>
                {row.label}
              </td>
              {TREND_COLS.map((col) => {
                const cellKey = `${row.key}:${col.key}`;
                const pct = alloc[cellKey] ?? 0;
                const isActive = cellKey === activeKey;
                return (
                  <td key={cellKey} className="p-1">
                    <div
                      className={cn(
                        "flex flex-col items-center justify-center rounded-lg py-2.5 px-3 transition-all",
                        allocColor(pct),
                        isActive
                          ? "ring-2 ring-blue-500 ring-offset-1 ring-offset-zinc-950 scale-105"
                          : "opacity-70 hover:opacity-100"
                      )}
                    >
                      <span className="text-sm font-bold">{Math.round(pct * 100)}%</span>
                      <span className="text-[10px] opacity-70 mt-0.5">allocation</span>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
