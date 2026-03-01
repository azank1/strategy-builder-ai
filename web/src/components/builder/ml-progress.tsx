"use client";

import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * MLProgressBar — visualizes ML pipeline execution stages
 *
 * Stages for LTPI trend system:
 *  1. ISP Labeling  →  2. Indicator Training  →  3. Feature Extraction
 *  4. Clustering    →  5. Strategy Optimization  →  6. Signal Composition
 *
 * Each stage can be: idle | running | complete | error
 * Shows elapsed time and optional sub-progress within a stage.
 * ─────────────────────────────────────────────────────────────────────────── */

export interface PipelineStage {
  id: string;
  label: string;
  description: string;
  status: "idle" | "running" | "complete" | "error";
  /** 0-100 progress within the stage */
  progress?: number;
  /** e.g. "Optimizing RSI parameters…" */
  detail?: string;
  /** Seconds elapsed */
  elapsed?: number;
}

interface Props {
  stages: PipelineStage[];
  /** Overall pipeline label */
  title?: string;
}

const STATUS_STYLES = {
  idle: {
    dot: "bg-zinc-700 border-zinc-600",
    line: "bg-zinc-800",
    text: "text-zinc-600",
  },
  running: {
    dot: "bg-blue-500 border-blue-400 animate-pulse",
    line: "bg-blue-500/30",
    text: "text-blue-400",
  },
  complete: {
    dot: "bg-emerald-500 border-emerald-400",
    line: "bg-emerald-500/30",
    text: "text-emerald-400",
  },
  error: {
    dot: "bg-red-500 border-red-400",
    line: "bg-red-500/30",
    text: "text-red-400",
  },
};

function formatElapsed(s: number | undefined): string {
  if (s === undefined) return "";
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function MLProgressBar({ stages, title }: Props) {
  const completedCount = stages.filter((s) => s.status === "complete").length;
  const hasError = stages.some((s) => s.status === "error");
  const isRunning = stages.some((s) => s.status === "running");
  const overallPct = stages.length > 0 ? (completedCount / stages.length) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Header + overall bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {title && <span className="text-sm font-medium text-zinc-200">{title}</span>}
          <span className="text-xs text-zinc-500">
            {completedCount}/{stages.length} stages
          </span>
        </div>
        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-xs text-blue-400">Processing…</span>
          </div>
        )}
        {hasError && (
          <span className="text-xs text-red-400">Pipeline error</span>
        )}
        {!isRunning && !hasError && completedCount === stages.length && stages.length > 0 && (
          <span className="text-xs text-emerald-400">Complete ✓</span>
        )}
      </div>

      {/* Overall progress bar */}
      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-700",
            hasError ? "bg-red-500" : isRunning ? "bg-blue-500" : "bg-emerald-500"
          )}
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Stage timeline */}
      <div className="space-y-1">
        {stages.map((stage, i) => {
          const styles = STATUS_STYLES[stage.status];
          const isLast = i === stages.length - 1;
          return (
            <div key={stage.id} className="flex gap-3">
              {/* Timeline dot + line */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "h-3 w-3 rounded-full border-2 flex-shrink-0 mt-0.5",
                    styles.dot
                  )}
                />
                {!isLast && (
                  <div className={cn("w-0.5 flex-1 min-h-[20px]", styles.line)} />
                )}
              </div>

              {/* Content */}
              <div className={cn("pb-3 flex-1 min-w-0", isLast && "pb-0")}>
                <div className="flex items-center gap-2">
                  <span className={cn("text-sm font-medium", styles.text)}>
                    {stage.label}
                  </span>
                  {stage.elapsed !== undefined && stage.status !== "idle" && (
                    <span className="text-[10px] font-mono text-zinc-600">
                      {formatElapsed(stage.elapsed)}
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-600 mt-0.5">{stage.description}</p>

                {/* Running stage detail + sub-progress */}
                {stage.status === "running" && (
                  <div className="mt-2 space-y-1.5">
                    {stage.detail && (
                      <p className="text-xs text-blue-400/80">{stage.detail}</p>
                    )}
                    {stage.progress !== undefined && (
                      <div className="h-1 rounded-full bg-zinc-800 overflow-hidden max-w-xs">
                        <div
                          className="h-full rounded-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${stage.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Error message */}
                {stage.status === "error" && stage.detail && (
                  <p className="text-xs text-red-400 mt-1">{stage.detail}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Preset stages for the LTPI ML pipeline */
export const LTPI_PIPELINE_STAGES: PipelineStage[] = [
  {
    id: "isp",
    label: "ISP Labeling",
    description: "Process intended signal period annotations",
    status: "idle",
  },
  {
    id: "train",
    label: "Indicator Training",
    description: "Bayesian optimization of indicator parameters",
    status: "idle",
  },
  {
    id: "features",
    label: "Feature Extraction",
    description: "Compute Sharpe, Omega, MAE, correlation metrics",
    status: "idle",
  },
  {
    id: "cluster",
    label: "Clustering",
    description: "PCA dimensionality reduction + K-Means grouping",
    status: "idle",
  },
  {
    id: "optimize",
    label: "Strategy Optimization",
    description: "Per-cluster Bayesian strategy training",
    status: "idle",
  },
  {
    id: "compose",
    label: "Signal Composition",
    description: "Quality × diversity weighted signal aggregation",
    status: "idle",
  },
];
