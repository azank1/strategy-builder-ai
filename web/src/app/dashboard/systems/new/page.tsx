"use client";

import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * System Type Selector — routes to the full builder page per type
 * ─────────────────────────────────────────────────────────────────────────── */

const SYSTEM_TYPES = [
  {
    key: "valuation",
    label: "Valuation System",
    description:
      "Build a multi-indicator valuation model using z-score normalization, outlier-robust statistics, and category-balanced scoring across fundamental, technical, and sentiment indicators.",
    features: [
      "15+ indicator portfolio with diversification rules",
      "Automated z-score computation with 5 outlier methods",
      "Live coherency analysis and validation feedback",
      "Structured research documentation per indicator",
    ],
    route: "/dashboard/systems/new/valuation",
    color: "blue",
  },
  {
    key: "trend",
    label: "Trend System",
    description:
      "Design a trend-following system combining technical and on-chain indicators with ML-powered optimization, intended signal period (ISP) labeling, and probabilistic clustering.",
    features: [
      "12 technical + 4-5 on-chain indicators",
      "Interactive ISP drawing on price charts",
      "Bayesian parameter optimization per indicator",
      "PCA + K-Means clustering with quality weighting",
    ],
    route: "/dashboard/systems/new/trend",
    color: "emerald",
  },
  {
    key: "momentum",
    label: "Momentum System",
    description:
      "Medium-term momentum signals using ML-trained indicators with probabilistic trend detection. Builds on the Trend system foundation with accelerated timeframes.",
    features: [
      "Probabilistic trend scoring",
      "Adaptive timeframe scaling",
      "Cross-validated signal composition",
    ],
    route: "#",
    disabled: true,
    color: "amber",
  },
  {
    key: "rotation",
    label: "Rotation System",
    description:
      "Multi-asset allocation signals that combine Valuation + Trend outputs across BTC, ETH, Gold, and equities to optimize portfolio rotation timing.",
    features: [
      "Cross-asset signal matrix",
      "Regime-aware allocation",
      "Portfolio-level risk management",
    ],
    route: "#",
    disabled: true,
    color: "violet",
  },
];

const COLOR_MAP: Record<string, { border: string; bg: string; text: string; badge: string }> = {
  blue: {
    border: "border-blue-500/40",
    bg: "bg-blue-500/5",
    text: "text-blue-400",
    badge: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  },
  emerald: {
    border: "border-emerald-500/40",
    bg: "bg-emerald-500/5",
    text: "text-emerald-400",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  amber: {
    border: "border-amber-500/30",
    bg: "bg-amber-500/5",
    text: "text-amber-400",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  violet: {
    border: "border-violet-500/30",
    bg: "bg-violet-500/5",
    text: "text-violet-400",
    badge: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  },
};

export default function NewSystemPage() {
  const router = useRouter();

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Create New System</h1>
        <p className="text-zinc-400 mt-2">
          Choose a system type to open the full builder interface.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SYSTEM_TYPES.map((t) => {
          const colors = COLOR_MAP[t.color];
          return (
            <button
              key={t.key}
              disabled={t.disabled}
              onClick={() => router.push(t.route)}
              className={cn(
                "rounded-xl border p-6 text-left transition-all group",
                t.disabled
                  ? "border-zinc-800 bg-zinc-900/30 text-zinc-600 cursor-not-allowed opacity-60"
                  : cn(
                      "border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900",
                      `hover:${colors.border}`
                    )
              )}
            >
              <div className="flex items-center gap-3 mb-3">
                <h3 className={cn("text-lg font-semibold", t.disabled ? "text-zinc-600" : "text-zinc-100")}>
                  {t.label}
                </h3>
                {t.disabled && (
                  <span className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">
                    Coming Soon
                  </span>
                )}
              </div>

              <p className="text-sm text-zinc-400 mb-4 leading-relaxed">{t.description}</p>

              <ul className="space-y-1.5">
                {t.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span className={cn("mt-0.5", t.disabled ? "text-zinc-700" : colors.text)}>•</span>
                    <span className={t.disabled ? "text-zinc-600" : "text-zinc-400"}>{f}</span>
                  </li>
                ))}
              </ul>

              {!t.disabled && (
                <div
                  className={cn(
                    "mt-5 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
                    colors.badge,
                    "group-hover:opacity-100 opacity-70"
                  )}
                >
                  Open Builder →
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
