"use client";

import { cn } from "@/lib/utils";
import type { BacktestMetrics } from "./engine";

/* ───────────────────────────────────────────────────────────────────────────
 * MetricsTable — Performance metrics grid with Sharpe, Sortino, Omega,
 * and supporting stats. Updates in real-time with the equity curve.
 * ─────────────────────────────────────────────────────────────────────────── */

function MetricCard({
  label,
  value,
  suffix = "",
  highlight = false,
  positive,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  highlight?: boolean;
  positive?: boolean;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-4 py-3">
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
        {label}
      </p>
      <p
        className={cn(
          "text-lg font-mono font-semibold",
          highlight
            ? positive !== undefined
              ? positive
                ? "text-emerald-400"
                : "text-red-400"
              : "text-white"
            : "text-zinc-200"
        )}
      >
        {value}
        {suffix}
      </p>
    </div>
  );
}

interface Props {
  metrics: BacktestMetrics;
  initialCapital: number;
}

export function MetricsTable({ metrics, initialCapital }: Props) {
  const finalCapital = initialCapital * (1 + metrics.totalReturn / 100);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <h3 className="text-sm font-medium text-zinc-300 mb-4">
        Performance Metrics
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Total Return"
          value={`${metrics.totalReturn >= 0 ? "+" : ""}${metrics.totalReturn.toFixed(2)}`}
          suffix="%"
          highlight
          positive={metrics.totalReturn >= 0}
        />
        <MetricCard
          label="Final Equity"
          value={`$${finalCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          highlight
          positive={finalCapital >= initialCapital}
        />
        <MetricCard
          label="Max Drawdown"
          value={metrics.maxDrawdown.toFixed(2)}
          suffix="%"
          highlight
          positive={false}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics.sharpeRatio.toFixed(2)}
          highlight
          positive={metrics.sharpeRatio > 0}
        />
        <MetricCard
          label="Sortino Ratio"
          value={metrics.sortinoRatio.toFixed(2)}
          highlight
          positive={metrics.sortinoRatio > 0}
        />
        <MetricCard
          label="Omega Ratio"
          value={metrics.omegaRatio.toFixed(2)}
          highlight
          positive={metrics.omegaRatio > 1}
        />
        <MetricCard
          label="Win Rate"
          value={metrics.winRate.toFixed(1)}
          suffix="%"
        />
        <MetricCard
          label="Round-Trips"
          value={metrics.completedTrades}
        />
        <MetricCard
          label="Avg Trade"
          value={`${metrics.avgTradeReturn >= 0 ? "+" : ""}${metrics.avgTradeReturn.toFixed(2)}`}
          suffix="%"
          highlight
          positive={metrics.avgTradeReturn >= 0}
        />
        <MetricCard
          label="Profit Factor"
          value={metrics.profitFactor.toFixed(2)}
          highlight
          positive={metrics.profitFactor > 1}
        />
      </div>
    </div>
  );
}
