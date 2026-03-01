"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import * as api from "@/lib/api";

import { Section } from "@/components/builder/section";
import { ScoreGauge } from "@/components/builder/score-gauge";
import { ValidationPanel } from "@/components/builder/validation-panel";
import { CoherencyHeatmap } from "@/components/builder/coherency-heatmap";
import { SignalMatrix } from "@/components/builder/signal-matrix";
import { IndicatorForm, type SDCAFormData } from "@/components/builder/indicator-form";

/* ───────────────────────────────────────────────────────────────────────────
 * Valuation Builder — power-form for creating SDCA systems
 *
 * 5 collapsible sections:
 *  1. System Setup       — name, asset, description
 *  2. Indicators         — table + inline add/edit form
 *  3. Validation         — live rule checking with counters
 *  4. Analysis           — coherency heatmap + z-score gauge
 *  5. Signal Output      — composite score, signal matrix, save
 * ─────────────────────────────────────────────────────────────────────────── */

const ASSET_OPTIONS = [
  { key: "btc", label: "Bitcoin", symbol: "BTC" },
  { key: "eth", label: "Ethereum", symbol: "ETH" },
  { key: "gold", label: "Gold", symbol: "XAU" },
  { key: "spx", label: "S&P 500", symbol: "SPX" },
];

interface Indicator {
  id: string;
  name: string;
  category: string;
  source_url: string;
  source_website: string;
  source_author?: string;
  provided_by: string;
  z_score: number;
  date_updated: string;
  comments: {
    why_chosen: string;
    how_it_works: string;
    scoring_logic: string;
  };
  has_decay: boolean;
  decay_description?: string;
  is_logarithmic: boolean;
  is_normalized: boolean;
}

export default function ValuationBuilderPage() {
  const router = useRouter();
  const { token, user } = useAuth();

  // ── Section 1: Setup State ──────────────────────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [asset, setAsset] = useState("btc");

  // ── Section 2: Indicators ───────────────────────────────────────────
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // ── Section 3: Validation ───────────────────────────────────────────
  const [validationErrors, setValidationErrors] = useState<api.ValidationIssue[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<api.ValidationIssue[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  // ── Section 4: Analysis ─────────────────────────────────────────────
  const [coherencyLabels, setCoherencyLabels] = useState<string[]>([]);
  const [coherencyMatrix, setCoherencyMatrix] = useState<number[][]>([]);
  const [coherencyOutliers, setCoherencyOutliers] = useState<Set<string>>(new Set());
  const [agreementRatio, setAgreementRatio] = useState<number | undefined>();

  // ── General ─────────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);

  // ── Derived ─────────────────────────────────────────────────────────
  const compositeZScore = useMemo(() => {
    if (indicators.length === 0) return 0;
    return indicators.reduce((s, i) => s + i.z_score, 0) / indicators.length;
  }, [indicators]);

  const categoryCounters = useMemo(() => {
    const counts: Record<string, number> = { fundamental: 0, technical: 0, sentiment: 0 };
    const mins: Record<string, number> = { fundamental: 5, technical: 5, sentiment: 2 };
    for (const ind of indicators) {
      counts[ind.category] = (counts[ind.category] || 0) + 1;
    }
    const result: Record<string, string> = {};
    for (const [cat, min] of Object.entries(mins)) {
      const count = counts[cat] || 0;
      result[cat] = count >= min ? `${count}/${min} ✓` : `${count}/${min}`;
    }
    return result;
  }, [indicators]);

  const valuationSignal = useMemo(() => {
    const z = compositeZScore;
    if (z <= -2) return "strongest_buy";
    if (z <= -1) return "buy";
    if (z >= 2) return "strongest_sell";
    if (z >= 1) return "sell";
    return "hold";
  }, [compositeZScore]);

  // ── Validate on indicator change ────────────────────────────────────
  const runValidation = useCallback(async () => {
    if (!token || indicators.length === 0) {
      setValidationErrors([]);
      setValidationWarnings([]);
      return;
    }
    setIsValidating(true);
    try {
      const systemData = {
        asset,
        indicators: indicators.map((ind) => ({
          name: ind.name,
          category: ind.category,
          source_url: ind.source_url,
          source_website: ind.source_website,
          source_author: ind.source_author || null,
          provided_by: ind.provided_by,
          z_score: ind.z_score,
          date_updated: ind.date_updated,
          comments: ind.comments,
          has_decay: ind.has_decay,
          decay_description: ind.decay_description || null,
          is_logarithmic: ind.is_logarithmic,
          is_normalized: ind.is_normalized,
        })),
        date_updated: new Date().toISOString().split("T")[0],
      };
      const result = await api.validateSystem(token, "valuation", systemData);
      setValidationErrors(result.errors);
      setValidationWarnings(result.warnings);
    } catch {
      // Silently handle — validation is non-blocking
    } finally {
      setIsValidating(false);
    }
  }, [token, indicators, asset]);

  useEffect(() => {
    const timer = setTimeout(runValidation, 500);
    return () => clearTimeout(timer);
  }, [runValidation]);

  // ── Coherency analysis on indicator change ──────────────────────────
  const runCoherency = useCallback(async () => {
    if (!token || indicators.length < 2) {
      setCoherencyLabels([]);
      setCoherencyMatrix([]);
      setCoherencyOutliers(new Set());
      setAgreementRatio(undefined);
      return;
    }
    try {
      const signals: Record<string, number[]> = {};
      for (const ind of indicators) {
        signals[ind.name] = [ind.z_score];
      }
      const result = await api.analyzeCoherency(token, signals);
      // Build labels from indicators and synthetic correlation matrix from alignment
      const names = indicators.map((i) => i.name);
      setCoherencyLabels(names);
      // Create a simple correlation matrix from per-indicator alignment values
      const alignment = result.per_indicator_alignment ?? {};
      const n = names.length;
      const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
      for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
          if (r === c) matrix[r][c] = 1;
          else {
            const a1 = alignment[names[r]] ?? 0;
            const a2 = alignment[names[c]] ?? 0;
            matrix[r][c] = parseFloat((a1 * a2).toFixed(2));
          }
        }
      }
      setCoherencyMatrix(matrix);
      setCoherencyOutliers(new Set(result.outlier_indicators ?? []));
      setAgreementRatio(result.agreement_ratio);
    } catch {
      // Non-blocking
    }
  }, [token, indicators]);

  useEffect(() => {
    const timer = setTimeout(runCoherency, 800);
    return () => clearTimeout(timer);
  }, [runCoherency]);

  // ── Add indicator handler ───────────────────────────────────────────
  const handleAddIndicator = (data: SDCAFormData) => {
    const newIndicator: Indicator = {
      id: crypto.randomUUID(),
      name: data.name,
      category: data.category,
      source_url: data.source_url,
      source_website: data.source_website,
      source_author: data.source_author || undefined,
      provided_by: data.provided_by,
      z_score: Number(data.z_score),
      date_updated: data.date_updated || new Date().toISOString().split("T")[0],
      comments: {
        why_chosen: data.why_chosen,
        how_it_works: data.how_it_works,
        scoring_logic: data.scoring_logic,
      },
      has_decay: data.has_decay,
      decay_description: data.decay_description || undefined,
      is_logarithmic: data.is_logarithmic,
      is_normalized: data.is_normalized,
    };
    setIndicators((prev) => [...prev, newIndicator]);
    setShowAddForm(false);
    toast.success(`Added "${data.name}"`);
  };

  const handleEditIndicator = (data: SDCAFormData) => {
    setIndicators((prev) =>
      prev.map((ind) =>
        ind.id === editingId
          ? {
              ...ind,
              name: data.name,
              category: data.category,
              source_url: data.source_url,
              source_website: data.source_website,
              source_author: data.source_author || undefined,
              provided_by: data.provided_by,
              z_score: Number(data.z_score),
              date_updated: data.date_updated,
              comments: {
                why_chosen: data.why_chosen,
                how_it_works: data.how_it_works,
                scoring_logic: data.scoring_logic,
              },
              has_decay: data.has_decay,
              decay_description: data.decay_description || undefined,
              is_logarithmic: data.is_logarithmic,
              is_normalized: data.is_normalized,
            }
          : ind
      )
    );
    setEditingId(null);
    toast.success("Indicator updated");
  };

  const handleRemoveIndicator = (id: string) => {
    setIndicators((prev) => prev.filter((ind) => ind.id !== id));
    toast("Indicator removed");
  };

  // ── Save / Create System ────────────────────────────────────────────
  const handleSave = async () => {
    if (!token || !name.trim()) {
      toast.error("System name is required");
      return;
    }
    setSubmitting(true);
    try {
      const systemData = {
        asset,
        indicators: indicators.map(({ id, ...rest }) => ({
          ...rest,
          source_author: rest.source_author || null,
          decay_description: rest.decay_description || null,
        })),
        date_updated: new Date().toISOString().split("T")[0],
      };
      await api.createSystem(token, {
        system_type: "valuation",
        asset,
        name: name.trim(),
        description: description.trim() || undefined,
        system_data: systemData,
      });
      toast.success("Valuation system created");
      router.push("/dashboard/systems");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to save system");
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = validationErrors.length === 0 && indicators.length >= 15;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-24">
      {/* ── Sticky Header ──────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 -mx-6 px-6 py-4 bg-zinc-950/90 backdrop-blur-lg border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard/systems/new")}
              className="text-sm text-zinc-500 hover:text-white transition-colors"
            >
              ← Back
            </button>
            <div>
              <h1 className="text-xl font-bold">
                {name || "New Valuation System"}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-zinc-500">{asset.toUpperCase()}</span>
                <span className="text-xs text-zinc-600">·</span>
                <span className="text-xs text-zinc-500">{indicators.length} indicators</span>
                <span className="text-xs text-zinc-600">·</span>
                <span
                  className={cn(
                    "text-xs font-medium",
                    isValid ? "text-emerald-400" : "text-amber-400"
                  )}
                >
                  {isValid ? "Valid ✓" : "Incomplete"}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-48">
              <ScoreGauge value={compositeZScore} label="Composite Z" />
            </div>
            <button
              onClick={handleSave}
              disabled={submitting || !name.trim()}
              className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Saving…" : "Save System"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Section 1: System Setup ────────────────────────────────────── */}
      <Section
        title="System Setup"
        description="Name your system and select the target asset."
        defaultOpen
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              System Name <span className="text-red-400">*</span>
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. BTC Valuation — Macro Composite"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Asset
            </label>
            <select
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            >
              {ASSET_OPTIONS.filter(
                (a) => user?.allowed_assets?.includes(a.key) ?? a.key === "btc"
              ).map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label} ({a.symbol})
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-3">
          <label className="block text-xs font-medium text-zinc-400 mb-1.5">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Optional: describe the methodology or thesis…"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 resize-none"
          />
        </div>
      </Section>

      {/* ── Section 2: Indicators ──────────────────────────────────────── */}
      <Section
        title="Indicators"
        description="Build your indicator portfolio. Min 15 total: 5 fundamental, 5 technical, 2 sentiment."
        badge={`${indicators.length} added`}
        defaultOpen
      >
        {/* Indicator Table */}
        {indicators.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-left">
                  <th className="pb-2 text-xs font-medium text-zinc-500">Name</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500">Category</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500">Source</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500 text-right">Z-Score</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {indicators.map((ind) => (
                  <tr key={ind.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/50">
                    <td className="py-2.5 text-zinc-200 font-medium">{ind.name}</td>
                    <td className="py-2.5">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-medium capitalize",
                          ind.category === "fundamental"
                            ? "bg-blue-500/10 text-blue-400"
                            : ind.category === "technical"
                            ? "bg-violet-500/10 text-violet-400"
                            : "bg-amber-500/10 text-amber-400"
                        )}
                      >
                        {ind.category}
                      </span>
                    </td>
                    <td className="py-2.5 text-xs text-zinc-500 max-w-[150px] truncate">
                      {ind.source_website}
                    </td>
                    <td className="py-2.5 text-right">
                      <span
                        className={cn(
                          "font-mono text-sm",
                          ind.z_score <= -1
                            ? "text-emerald-400"
                            : ind.z_score >= 1
                            ? "text-red-400"
                            : "text-zinc-400"
                        )}
                      >
                        {ind.z_score >= 0 ? "+" : ""}
                        {ind.z_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setEditingId(ind.id)}
                          className="text-xs text-zinc-500 hover:text-blue-400 transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleRemoveIndicator(ind.id)}
                          className="text-xs text-zinc-500 hover:text-red-400 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Edit form (inline) */}
        {editingId && (
          <div className="mt-4">
            <IndicatorForm
              mode="valuation"
              defaultValues={(() => {
                const ind = indicators.find((i) => i.id === editingId);
                if (!ind) return {};
                return {
                  name: ind.name,
                  category: ind.category as "fundamental" | "technical" | "sentiment",
                  source_url: ind.source_url,
                  source_website: ind.source_website,
                  source_author: ind.source_author || "",
                  provided_by: ind.provided_by as "own_research" | "reference_sheet",
                  z_score: ind.z_score,
                  date_updated: ind.date_updated,
                  why_chosen: ind.comments.why_chosen,
                  how_it_works: ind.comments.how_it_works,
                  scoring_logic: ind.comments.scoring_logic,
                  has_decay: ind.has_decay,
                  decay_description: ind.decay_description || "",
                  is_logarithmic: ind.is_logarithmic,
                  is_normalized: ind.is_normalized,
                };
              })()}
              onSubmit={(data) => handleEditIndicator(data as SDCAFormData)}
              onCancel={() => setEditingId(null)}
            />
          </div>
        )}

        {/* Add new form */}
        {showAddForm ? (
          <div className="mt-4">
            <IndicatorForm
              mode="valuation"
              onSubmit={(data) => handleAddIndicator(data as SDCAFormData)}
              onCancel={() => setShowAddForm(false)}
            />
          </div>
        ) : (
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 w-full rounded-lg border border-dashed border-zinc-700 py-3 text-sm text-zinc-500 hover:border-blue-500 hover:text-blue-400 transition-colors"
          >
            + Add Indicator
          </button>
        )}
      </Section>

      {/* ── Section 3: Validation Dashboard ────────────────────────────── */}
      <Section
        title="Validation"
        description="Real-time rule checking against the system construction requirements."
        badge={isValid ? "Passed" : `${validationErrors.length} issues`}
        defaultOpen={indicators.length > 0}
      >
        <ValidationPanel
          errors={validationErrors}
          warnings={validationWarnings}
          isValid={isValid}
          isLoading={isValidating}
          counters={categoryCounters}
        />
      </Section>

      {/* ── Section 4: Analysis ────────────────────────────────────────── */}
      <Section
        title="Analysis"
        description="Coherency analysis, Z-score distribution, and indicator agreement."
        defaultOpen={indicators.length >= 3}
      >
        <div className="space-y-6">
          {/* Z-Score Gauge (large) */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <h4 className="text-xs font-medium text-zinc-500 mb-3">Composite Z-Score</h4>
            <ScoreGauge value={compositeZScore} label="Overall Valuation" />
            <div className="mt-3 grid grid-cols-3 gap-3">
              {Object.entries(
                indicators.reduce((acc, ind) => {
                  if (!acc[ind.category]) acc[ind.category] = [];
                  acc[ind.category].push(ind.z_score);
                  return acc;
                }, {} as Record<string, number[]>)
              ).map(([cat, scores]) => {
                const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
                return (
                  <div key={cat} className="text-center">
                    <div className="text-[10px] text-zinc-500 capitalize mb-1">{cat}</div>
                    <div
                      className={cn(
                        "text-sm font-mono font-bold",
                        avg <= -1 ? "text-emerald-400" : avg >= 1 ? "text-red-400" : "text-zinc-300"
                      )}
                    >
                      {avg >= 0 ? "+" : ""}
                      {avg.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Coherency Heatmap */}
          {indicators.length >= 2 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
              <h4 className="text-xs font-medium text-zinc-500 mb-3">
                Indicator Coherency Matrix
              </h4>
              <CoherencyHeatmap
                labels={coherencyLabels}
                correlations={coherencyMatrix}
                outliers={coherencyOutliers}
                agreementRatio={agreementRatio}
                compact={indicators.length > 8}
              />
            </div>
          )}
        </div>
      </Section>

      {/* ── Section 5: Signal Output ───────────────────────────────────── */}
      <Section
        title="Signal Output"
        description="Preview the allocation signal this system would produce."
        defaultOpen={indicators.length >= 5}
      >
        <div className="space-y-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <SignalMatrix valuationSignal={valuationSignal} />
          </div>
          <p className="text-xs text-zinc-600">
            Valuation signal is combined with a Trend system to produce the final allocation.
            The highlighted column will activate once you create or link a Trend system.
          </p>
        </div>
      </Section>
    </div>
  );
}
