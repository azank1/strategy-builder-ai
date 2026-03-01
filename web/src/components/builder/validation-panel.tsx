"use client";

import type { ValidationIssue } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * ValidationPanel — live validation feedback for system builders
 *
 * Shows structured errors, warnings, and passes per rule with fix hints.
 * Updates as the user modifies their system (debounced externally).
 * ─────────────────────────────────────────────────────────────────────────── */

interface Props {
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  isValid: boolean;
  isLoading?: boolean;
  /** Category progress counters, e.g. { fundamental: "3/5", technical: "6/5 ✓" } */
  counters?: Record<string, string>;
}

const SEVERITY_STYLES = {
  error: {
    icon: "✕",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    text: "text-red-400",
    iconBg: "bg-red-500/20",
  },
  warning: {
    icon: "!",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    text: "text-amber-400",
    iconBg: "bg-amber-500/20",
  },
};

export function ValidationPanel({ errors, warnings, isValid, isLoading, counters }: Props) {
  const total = errors.length + warnings.length;

  return (
    <div className="space-y-4">
      {/* Status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isLoading ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-600 border-t-blue-500" />
          ) : isValid ? (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
              ✓
            </div>
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 text-red-400 text-xs font-bold">
              {errors.length}
            </div>
          )}
          <span className={cn("text-sm font-medium", isValid ? "text-emerald-400" : "text-red-400")}>
            {isLoading ? "Validating…" : isValid ? "All checks passed" : `${errors.length} error${errors.length !== 1 ? "s" : ""}`}
          </span>
          {warnings.length > 0 && !isLoading && (
            <span className="text-xs text-amber-400">
              · {warnings.length} warning{warnings.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Category counters */}
      {counters && Object.keys(counters).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(counters).map(([cat, count]) => {
            const met = count.includes("✓");
            return (
              <span
                key={cat}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium capitalize",
                  met
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                )}
              >
                {cat}: {count}
              </span>
            );
          })}
        </div>
      )}

      {/* Issue list */}
      {total > 0 && !isLoading && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {errors.map((issue, i) => (
            <IssueRow key={`e-${i}`} issue={issue} severity="error" />
          ))}
          {warnings.map((issue, i) => (
            <IssueRow key={`w-${i}`} issue={issue} severity="warning" />
          ))}
        </div>
      )}
    </div>
  );
}

function IssueRow({ issue, severity }: { issue: ValidationIssue; severity: "error" | "warning" }) {
  const styles = SEVERITY_STYLES[severity];
  return (
    <div className={cn("flex items-start gap-3 rounded-lg border px-3 py-2.5", styles.bg, styles.border)}>
      <span
        className={cn(
          "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
          styles.iconBg,
          styles.text
        )}
      >
        {styles.icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm", styles.text)}>{issue.message}</p>
        <div className="mt-0.5 flex items-center gap-2">
          <span className="text-[10px] font-mono text-zinc-600">{issue.rule}</span>
          {issue.indicator_name && (
            <span className="text-[10px] text-zinc-500">· {issue.indicator_name}</span>
          )}
        </div>
      </div>
    </div>
  );
}
