"use client";

import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * CoherencyHeatmap — pairwise indicator correlation matrix
 *
 * Displays a grid of correlation cells colored from red (-1) to green (+1).
 * Highlights outlier indicators and shows agreement ratio.
 * ─────────────────────────────────────────────────────────────────────────── */

interface Props {
  /** Indicator names */
  labels: string[];
  /** Row-major correlation matrix (labels.length × labels.length) */
  correlations: number[][];
  /** Set of indicator names flagged as outliers */
  outliers?: Set<string>;
  /** Overall agreement ratio 0-1 */
  agreementRatio?: number;
  /** Compact mode for smaller containers */
  compact?: boolean;
}

function corrColor(v: number): string {
  // -1 (red) → 0 (zinc) → +1 (emerald)
  if (v >= 0.6) return "bg-emerald-500/40 text-emerald-300";
  if (v >= 0.3) return "bg-emerald-500/20 text-emerald-400";
  if (v >= -0.3) return "bg-zinc-800 text-zinc-400";
  if (v >= -0.6) return "bg-red-500/20 text-red-400";
  return "bg-red-500/40 text-red-300";
}

function truncate(s: string, max: number) {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

export function CoherencyHeatmap({
  labels,
  correlations,
  outliers = new Set(),
  agreementRatio,
  compact = false,
}: Props) {
  const n = labels.length;
  const cellSize = compact ? "w-9 h-9 text-[10px]" : "w-11 h-11 text-xs";

  if (n === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 text-center text-sm text-zinc-500">
        Add at least 2 indicators to see coherency analysis
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      {agreementRatio !== undefined && (
        <div className="flex items-center gap-3">
          <div className="text-xs text-zinc-500">Agreement</div>
          <div className="flex-1 h-2 rounded-full bg-zinc-800 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                agreementRatio >= 0.7 ? "bg-emerald-500" : agreementRatio >= 0.4 ? "bg-amber-500" : "bg-red-500"
              )}
              style={{ width: `${Math.round(agreementRatio * 100)}%` }}
            />
          </div>
          <div className="text-xs font-mono text-zinc-400">{(agreementRatio * 100).toFixed(0)}%</div>
        </div>
      )}

      {/* Matrix */}
      <div className="overflow-x-auto">
        <div className="inline-grid gap-0.5" style={{ gridTemplateColumns: `auto repeat(${n}, min-content)` }}>
          {/* Top-left empty */}
          <div />
          {/* Column headers */}
          {labels.map((l) => (
            <div
              key={`col-${l}`}
              className={cn(
                "flex items-end justify-center pb-1 text-[10px] text-zinc-500 font-mono",
                cellSize,
                outliers.has(l) && "text-red-400"
              )}
              title={l}
            >
              <span className="rotate-[-45deg] origin-bottom-left whitespace-nowrap">
                {truncate(l, 8)}
              </span>
            </div>
          ))}

          {/* Rows */}
          {labels.map((rowLabel, r) => (
            <>
              {/* Row label */}
              <div
                key={`row-${rowLabel}`}
                className={cn(
                  "flex items-center pr-2 text-[10px] text-zinc-500 font-mono",
                  outliers.has(rowLabel) && "text-red-400"
                )}
                title={rowLabel}
              >
                {truncate(rowLabel, 10)}
              </div>
              {/* Cells */}
              {labels.map((_, c) => {
                const val = correlations[r]?.[c] ?? 0;
                const isDiag = r === c;
                return (
                  <div
                    key={`cell-${r}-${c}`}
                    className={cn(
                      "flex items-center justify-center rounded-sm font-mono",
                      cellSize,
                      isDiag ? "bg-zinc-700/50 text-zinc-500" : corrColor(val)
                    )}
                    title={`${rowLabel} × ${labels[c]}: ${val.toFixed(2)}`}
                  >
                    {isDiag ? "1" : val.toFixed(1)}
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>

      {/* Outlier callout */}
      {outliers.size > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2">
          <span className="text-amber-400 text-xs">⚠</span>
          <p className="text-xs text-amber-400">
            <span className="font-medium">Outlier indicator{outliers.size > 1 ? "s" : ""}:</span>{" "}
            {[...outliers].join(", ")} — consider reviewing or replacing.
          </p>
        </div>
      )}
    </div>
  );
}
