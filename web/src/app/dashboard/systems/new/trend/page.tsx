"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import * as api from "@/lib/api";

import { Section } from "@/components/builder/section";
import { TrendGauge } from "@/components/builder/score-gauge";
import { ValidationPanel } from "@/components/builder/validation-panel";
import { PriceChart, type ISPZone } from "@/components/builder/price-chart";
import { IndicatorForm, type LTPIFormData } from "@/components/builder/indicator-form";
import { MLProgressBar, LTPI_PIPELINE_STAGES, type PipelineStage } from "@/components/builder/ml-progress";

/* ───────────────────────────────────────────────────────────────────────────
 * Trend Builder — power-form for creating LTPI systems
 *
 * 6 collapsible sections:
 *  1. System Setup        — name, asset, timeframe
 *  2. Intended Signal Period — interactive price chart with ISP drawing
 *  3. Indicators          — technical_btc + on_chain table + forms
 *  4. Validation          — live rule checking
 *  5. ML Pipeline         — stage visualization for optimization
 *  6. Signal Output       — trend ratio, signal matrix, save
 * ─────────────────────────────────────────────────────────────────────────── */

const ASSET_OPTIONS = [
  { key: "btc", label: "Bitcoin", symbol: "BTC" },
  { key: "eth", label: "Ethereum", symbol: "ETH" },
  { key: "gold", label: "Gold", symbol: "XAU" },
  { key: "spx", label: "S&P 500", symbol: "SPX" },
];

const TIMEFRAME_OPTIONS = [
  { value: "1D", label: "Daily" },
  { value: "3D", label: "3-Day" },
  { value: "1W", label: "Weekly" },
];

interface TrendIndicator {
  id: string;
  name: string;
  category: "technical_btc" | "on_chain";
  source_url: string;
  source_website: string;
  author: string;
  indicator_type: string;
  scoring_criteria: string;
  comment: string;
  score: number;
  repaints: boolean;
}

interface ISPPoint {
  date: string;
  direction: "long" | "short";
}

export default function TrendBuilderPage() {
  const router = useRouter();
  const { token, user } = useAuth();

  // ── Section 1: Setup ────────────────────────────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [asset, setAsset] = useState("btc");
  const [timeframe, setTimeframe] = useState("1W");

  // ── Section 2: ISP ──────────────────────────────────────────────────
  const [ispPoints, setIspPoints] = useState<ISPPoint[]>([]);
  const [ispDrawMode, setIspDrawMode] = useState<"long" | "short" | null>(null);
  const [priceData, setPriceData] = useState<api.PricePoint[]>([]);
  const [loadingPrices, setLoadingPrices] = useState(false);

  // ── Section 3: Indicators ───────────────────────────────────────────
  const [indicators, setIndicators] = useState<TrendIndicator[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // ── Section 4: Validation ───────────────────────────────────────────
  const [validationErrors, setValidationErrors] = useState<api.ValidationIssue[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<api.ValidationIssue[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  // ── Section 5: ML Pipeline ──────────────────────────────────────────
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>(
    LTPI_PIPELINE_STAGES.map((s) => ({ ...s }))
  );

  // ── General ─────────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);

  // ── Derived ─────────────────────────────────────────────────────────
  const techBtc = useMemo(() => indicators.filter((i) => i.category === "technical_btc"), [indicators]);
  const onChain = useMemo(() => indicators.filter((i) => i.category === "on_chain"), [indicators]);
  const compositeScore = useMemo(() => indicators.reduce((s, i) => s + i.score, 0), [indicators]);
  const trendRatio = useMemo(
    () => (indicators.length > 0 ? compositeScore / indicators.length : 0),
    [compositeScore, indicators.length]
  );

  const trendSignal = useMemo(() => {
    if (trendRatio > 0.2) return "uptrend";
    if (trendRatio < -0.2) return "downtrend";
    return "neutral";
  }, [trendRatio]);

  const ispTradeCount = useMemo(() => {
    if (ispPoints.length < 2) return 0;
    let changes = 0;
    for (let i = 1; i < ispPoints.length; i++) {
      if (ispPoints[i].direction !== ispPoints[i - 1].direction) changes++;
    }
    return changes;
  }, [ispPoints]);

  // ISP zones for chart visualization
  const ispZones: ISPZone[] = useMemo(() => {
    if (ispPoints.length < 2) return [];
    const zones: ISPZone[] = [];
    let zoneStart = ispPoints[0];
    for (let i = 1; i < ispPoints.length; i++) {
      if (ispPoints[i].direction !== zoneStart.direction || i === ispPoints.length - 1) {
        zones.push({
          start: zoneStart.date,
          end: ispPoints[i].date,
          signal: zoneStart.direction === "long" ? "buy" : "sell",
        });
        zoneStart = ispPoints[i];
      }
    }
    return zones;
  }, [ispPoints]);

  // ── Load price data ─────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    const loadPrices = async () => {
      setLoadingPrices(true);
      try {
        const data = await api.getPriceData(token, asset, "2018-01-01");
        setPriceData(data.data);
      } catch {
        // Prices may fail for non-BTC in free tier
      } finally {
        setLoadingPrices(false);
      }
    };
    loadPrices();
  }, [token, asset]);

  // ── ISP chart click handler ─────────────────────────────────────────
  const handleChartClick = useCallback(
    (date: string) => {
      if (!ispDrawMode) return;
      setIspPoints((prev) => {
        // Insert in date order, remove duplicates
        const filtered = prev.filter((p) => p.date !== date);
        const newPoint: ISPPoint = { date, direction: ispDrawMode };
        const merged = [...filtered, newPoint].sort(
          (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
        );
        return merged;
      });
    },
    [ispDrawMode]
  );

  // ── Validate on indicator/ISP change ────────────────────────────────
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
        technical_btc: techBtc.map(({ id, ...rest }) => rest),
        on_chain: onChain.map(({ id, ...rest }) => rest),
        isp: ispPoints.length > 0
          ? {
              start_date: ispPoints[0]?.date || "2018-01-01",
              end_date: ispPoints[ispPoints.length - 1]?.date || new Date().toISOString().split("T")[0],
              timeframe,
              signals: ispPoints.map((p) => ({ date: p.date, direction: p.direction })),
            }
          : null,
        date_updated: new Date().toISOString().split("T")[0],
      };
      const result = await api.validateSystem(token, "trend", systemData);
      setValidationErrors(result.errors);
      setValidationWarnings(result.warnings);
    } catch {
      // Non-blocking
    } finally {
      setIsValidating(false);
    }
  }, [token, indicators, ispPoints, asset, timeframe, techBtc, onChain]);

  useEffect(() => {
    const timer = setTimeout(runValidation, 500);
    return () => clearTimeout(timer);
  }, [runValidation]);

  // ── Add/Edit/Remove indicators ──────────────────────────────────────
  const handleAddIndicator = (data: LTPIFormData) => {
    const newInd: TrendIndicator = {
      id: crypto.randomUUID(),
      name: data.name,
      category: data.category,
      source_url: data.source_url,
      source_website: data.source_website,
      author: data.author,
      indicator_type: data.indicator_type,
      scoring_criteria: data.scoring_criteria,
      comment: data.comment,
      score: Number(data.score),
      repaints: false,
    };
    setIndicators((prev) => [...prev, newInd]);
    setShowAddForm(false);
    toast.success(`Added "${data.name}"`);
  };

  const handleEditIndicator = (data: LTPIFormData) => {
    setIndicators((prev) =>
      prev.map((ind) =>
        ind.id === editingId
          ? {
              ...ind,
              name: data.name,
              category: data.category,
              source_url: data.source_url,
              source_website: data.source_website,
              author: data.author,
              indicator_type: data.indicator_type,
              scoring_criteria: data.scoring_criteria,
              comment: data.comment,
              score: Number(data.score),
            }
          : ind
      )
    );
    setEditingId(null);
    toast.success("Indicator updated");
  };

  const handleRemoveIndicator = (id: string) => {
    setIndicators((prev) => prev.filter((i) => i.id !== id));
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
        technical_btc: techBtc.map(({ id, ...rest }) => rest),
        on_chain: onChain.map(({ id, ...rest }) => rest),
        isp: ispPoints.length > 0
          ? {
              start_date: ispPoints[0]?.date,
              end_date: ispPoints[ispPoints.length - 1]?.date,
              timeframe,
              signals: ispPoints.map((p) => ({ date: p.date, direction: p.direction })),
            }
          : null,
        date_updated: new Date().toISOString().split("T")[0],
      };
      await api.createSystem(token, {
        system_type: "trend",
        asset,
        name: name.trim(),
        description: description.trim() || undefined,
        system_data: systemData,
      });
      toast.success("Trend system created");
      router.push("/dashboard/systems");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to save system");
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = validationErrors.length === 0 && techBtc.length === 12 && onChain.length >= 4;

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
                {name || "New Trend System"}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-zinc-500">{asset.toUpperCase()}</span>
                <span className="text-xs text-zinc-600">·</span>
                <span className="text-xs text-zinc-500">{indicators.length} indicators</span>
                <span className="text-xs text-zinc-600">·</span>
                <span className="text-xs text-zinc-500">{ispPoints.length} ISP points</span>
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
              <TrendGauge value={trendRatio} />
            </div>
            <button
              onClick={handleSave}
              disabled={submitting || !name.trim()}
              className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Saving…" : "Save System"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Section 1: System Setup ────────────────────────────────────── */}
      <Section
        title="System Setup"
        description="Name your trend system and configure the target asset and timeframe."
        defaultOpen
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              System Name <span className="text-red-400">*</span>
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. BTC Weekly Trend — Full On-Chain"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Asset
            </label>
            <select
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500 focus:outline-none"
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
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">
              Timeframe
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500 focus:outline-none"
            >
              {TIMEFRAME_OPTIONS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label} ({t.value})
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
            placeholder="Optional: describe the trend detection methodology…"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none resize-none"
          />
        </div>
      </Section>

      {/* ── Section 2: Intended Signal Period ──────────────────────────── */}
      <Section
        title="Intended Signal Period (ISP)"
        description="Draw your ideal buy/sell signals on the price chart. This defines the trend behavior your indicators should replicate. Min 11 trades required."
        badge={`${ispTradeCount} trades`}
        defaultOpen
      >
        {/* Draw mode toolbar */}
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs text-zinc-500">Draw mode:</span>
          <button
            onClick={() => setIspDrawMode(ispDrawMode === "long" ? null : "long")}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
              ispDrawMode === "long"
                ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                : "border-zinc-700 bg-zinc-900 text-zinc-500 hover:text-zinc-300"
            )}
          >
            ▲ Long (Buy)
          </button>
          <button
            onClick={() => setIspDrawMode(ispDrawMode === "short" ? null : "short")}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
              ispDrawMode === "short"
                ? "border-red-500 bg-red-500/10 text-red-400"
                : "border-zinc-700 bg-zinc-900 text-zinc-500 hover:text-zinc-300"
            )}
          >
            ▼ Short (Sell)
          </button>
          {ispPoints.length > 0 && (
            <button
              onClick={() => setIspPoints([])}
              className="text-xs text-zinc-600 hover:text-red-400 transition-colors ml-auto"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Price chart */}
        {loadingPrices ? (
          <div className="flex items-center justify-center h-80 rounded-xl border border-zinc-800 bg-zinc-900/50">
            <div className="flex items-center gap-2 text-sm text-zinc-500">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-emerald-500" />
              Loading price data…
            </div>
          </div>
        ) : (
          <PriceChart
            data={priceData}
            ispZones={ispZones}
            onChartClick={(date) => handleChartClick(date)}
            height={360}
          />
        )}

        {/* ISP info */}
        {ispDrawMode && (
          <p className="text-xs text-zinc-500 mt-2">
            Click on the chart to place {ispDrawMode === "long" ? "buy" : "sell"} signal points.
            Points are sorted by date automatically.
          </p>
        )}

        {ispTradeCount > 0 && (
          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Trade count:</span>
              <span
                className={cn(
                  "text-sm font-mono font-bold",
                  ispTradeCount >= 11 ? "text-emerald-400" : "text-amber-400"
                )}
              >
                {ispTradeCount}
              </span>
              <span className="text-[10px] text-zinc-600">(min 11)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Signal points:</span>
              <span className="text-sm font-mono text-zinc-300">{ispPoints.length}</span>
            </div>
          </div>
        )}
      </Section>

      {/* ── Section 3: Indicators ──────────────────────────────────────── */}
      <Section
        title="Indicators"
        description="Build your indicator set. Exactly 12 Technical BTC + 4-5 On-Chain indicators."
        badge={`${techBtc.length} tech · ${onChain.length} on-chain`}
        defaultOpen
      >
        {/* Category tabs */}
        <div className="flex gap-4 mb-4">
          <div
            className={cn(
              "flex-1 rounded-lg border p-3 text-center",
              techBtc.length === 12
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-zinc-700 bg-zinc-900"
            )}
          >
            <div className="text-lg font-bold text-zinc-200">{techBtc.length}/12</div>
            <div className="text-[10px] text-zinc-500">Technical BTC</div>
          </div>
          <div
            className={cn(
              "flex-1 rounded-lg border p-3 text-center",
              onChain.length >= 4 && onChain.length <= 5
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-zinc-700 bg-zinc-900"
            )}
          >
            <div className="text-lg font-bold text-zinc-200">{onChain.length}/4-5</div>
            <div className="text-[10px] text-zinc-500">On-Chain</div>
          </div>
        </div>

        {/* Indicator table */}
        {indicators.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-left">
                  <th className="pb-2 text-xs font-medium text-zinc-500">Name</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500">Category</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500">Type</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500">Author</th>
                  <th className="pb-2 text-xs font-medium text-zinc-500 text-center">Score</th>
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
                          "rounded-full px-2 py-0.5 text-[10px] font-medium",
                          ind.category === "technical_btc"
                            ? "bg-violet-500/10 text-violet-400"
                            : "bg-cyan-500/10 text-cyan-400"
                        )}
                      >
                        {ind.category === "technical_btc" ? "Technical" : "On-Chain"}
                      </span>
                    </td>
                    <td className="py-2.5 text-xs text-zinc-500">{ind.indicator_type}</td>
                    <td className="py-2.5 text-xs text-zinc-500">{ind.author}</td>
                    <td className="py-2.5 text-center">
                      <span
                        className={cn(
                          "inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold",
                          ind.score === 1
                            ? "bg-emerald-500/20 text-emerald-400"
                            : ind.score === -1
                            ? "bg-red-500/20 text-red-400"
                            : "bg-zinc-800 text-zinc-500"
                        )}
                      >
                        {ind.score > 0 ? "+" : ""}
                        {ind.score}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setEditingId(ind.id)}
                          className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors"
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

        {/* Edit form */}
        {editingId && (
          <div className="mt-4">
            <IndicatorForm
              mode="trend"
              defaultValues={(() => {
                const ind = indicators.find((i) => i.id === editingId);
                if (!ind) return {};
                return {
                  name: ind.name,
                  category: ind.category,
                  source_url: ind.source_url,
                  source_website: ind.source_website,
                  author: ind.author,
                  indicator_type: ind.indicator_type,
                  scoring_criteria: ind.scoring_criteria,
                  comment: ind.comment,
                  score: ind.score,
                  repaints: false,
                };
              })()}
              onSubmit={(data) => handleEditIndicator(data as LTPIFormData)}
              onCancel={() => setEditingId(null)}
            />
          </div>
        )}

        {/* Add form */}
        {showAddForm ? (
          <div className="mt-4">
            <IndicatorForm
              mode="trend"
              onSubmit={(data) => handleAddIndicator(data as LTPIFormData)}
              onCancel={() => setShowAddForm(false)}
            />
          </div>
        ) : (
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 w-full rounded-lg border border-dashed border-zinc-700 py-3 text-sm text-zinc-500 hover:border-emerald-500 hover:text-emerald-400 transition-colors"
          >
            + Add Indicator
          </button>
        )}
      </Section>

      {/* ── Section 4: Validation ──────────────────────────────────────── */}
      <Section
        title="Validation"
        description="Real-time rule checking: indicator counts, author uniqueness, ISP trades, no repainting."
        badge={isValid ? "Passed" : `${validationErrors.length} issues`}
        defaultOpen={indicators.length > 0}
      >
        <ValidationPanel
          errors={validationErrors}
          warnings={validationWarnings}
          isValid={isValid}
          isLoading={isValidating}
          counters={{
            "technical btc": techBtc.length === 12 ? `${techBtc.length}/12 ✓` : `${techBtc.length}/12`,
            "on-chain": onChain.length >= 4 ? `${onChain.length}/4-5 ✓` : `${onChain.length}/4`,
            "ISP trades": ispTradeCount >= 11 ? `${ispTradeCount} ✓` : `${ispTradeCount}/11`,
          }}
        />
      </Section>

      {/* ── Section 5: ML Pipeline ─────────────────────────────────────── */}
      <Section
        title="ML Pipeline"
        description="Machine learning optimization stages. Train indicators against your ISP, cluster them for diversity, and compose the final signal."
      >
        <MLProgressBar stages={pipelineStages} title="Trend System Pipeline" />
        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-zinc-600">
            Pipeline requires a valid system (all indicators + ISP with 11+ trades).
          </p>
          <button
            disabled={!isValid}
            onClick={() => {
              // Simulate pipeline progress for MVP
              toast.info("ML pipeline will be available after MLTPI engine integration");
            }}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              isValid
                ? "bg-emerald-600 text-white hover:bg-emerald-500"
                : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
            )}
          >
            Run Pipeline
          </button>
        </div>
      </Section>

      {/* ── Section 6: Signal Output ───────────────────────────────────── */}
      <Section
        title="Signal Output"
        description="Live trend ratio and composite score from your indicator set."
        defaultOpen={indicators.length >= 4}
      >
        <div className="space-y-4">
          {/* Score summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-center">
              <div className="text-[10px] text-zinc-500 mb-1">Composite Score</div>
              <div
                className={cn(
                  "text-2xl font-bold font-mono",
                  compositeScore > 0
                    ? "text-emerald-400"
                    : compositeScore < 0
                    ? "text-red-400"
                    : "text-zinc-400"
                )}
              >
                {compositeScore > 0 ? "+" : ""}{compositeScore}
              </div>
              <div className="text-[10px] text-zinc-600">
                of ±{indicators.length}
              </div>
            </div>
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-center">
              <div className="text-[10px] text-zinc-500 mb-1">Trend Ratio</div>
              <div
                className={cn(
                  "text-2xl font-bold font-mono",
                  trendRatio > 0.2
                    ? "text-emerald-400"
                    : trendRatio < -0.2
                    ? "text-red-400"
                    : "text-zinc-400"
                )}
              >
                {trendRatio >= 0 ? "+" : ""}{trendRatio.toFixed(3)}
              </div>
            </div>
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-center">
              <div className="text-[10px] text-zinc-500 mb-1">Signal</div>
              <div
                className={cn(
                  "text-lg font-bold capitalize",
                  trendSignal === "uptrend"
                    ? "text-emerald-400"
                    : trendSignal === "downtrend"
                    ? "text-red-400"
                    : "text-zinc-400"
                )}
              >
                {trendSignal === "uptrend" ? "▲" : trendSignal === "downtrend" ? "▼" : "—"}{" "}
                {trendSignal}
              </div>
            </div>
          </div>

          {/* Trend gauge */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <TrendGauge value={trendRatio} />
          </div>

          <p className="text-xs text-zinc-600">
            Trend signal is combined with a Valuation system to produce the final allocation in the signal matrix.
          </p>
        </div>
      </Section>
    </div>
  );
}
