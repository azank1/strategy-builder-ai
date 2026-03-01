"use client";

import { useForm, Controller } from "react-hook-form";
import { cn } from "@/lib/utils";

/* ───────────────────────────────────────────────────────────────────────────
 * IndicatorForm — reusable add/edit form for SDCA and LTPI indicators
 *
 * Adapts fields based on `mode`:
 *  - "valuation" → SDCA fields (z-score slider, 3 comment fields, decay)
 *  - "trend"     → LTPI fields (score ±1, author, type, scoring criteria)
 * ─────────────────────────────────────────────────────────────────────────── */

// ── Types ────────────────────────────────────────────────────────────────────

export interface SDCAFormData {
  name: string;
  category: "fundamental" | "technical" | "sentiment";
  source_url: string;
  source_website: string;
  source_author: string;
  provided_by: "own_research" | "reference_sheet";
  z_score: number;
  date_updated: string;
  why_chosen: string;
  how_it_works: string;
  scoring_logic: string;
  has_decay: boolean;
  decay_description: string;
  is_logarithmic: boolean;
  is_normalized: boolean;
}

export interface LTPIFormData {
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFormData = Record<string, any>;

interface Props {
  mode: "valuation" | "trend";
  /** Pre-fill values for editing */
  defaultValues?: Partial<AnyFormData>;
  onSubmit: (data: AnyFormData) => void;
  onCancel?: () => void;
  isLoading?: boolean;
}

// ── Shared Atoms ─────────────────────────────────────────────────────────────

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block text-xs font-medium text-zinc-400 mb-1.5">
      {children}
      {required && <span className="text-red-400 ml-0.5">*</span>}
    </label>
  );
}

function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { className?: string }) {
  return (
    <input
      className={cn(
        "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200",
        "placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50",
        className
      )}
      {...props}
    />
  );
}

function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { className?: string }) {
  return (
    <textarea
      className={cn(
        "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 resize-none",
        "placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50",
        className
      )}
      rows={3}
      {...props}
    />
  );
}

function Select({
  options,
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & {
  options: { value: string; label: string }[];
  className?: string;
}) {
  return (
    <select
      className={cn(
        "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200",
        "focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50",
        className
      )}
      {...props}
    >
      <option value="">Select…</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

const SDCA_CATEGORIES = [
  { value: "fundamental", label: "Fundamental" },
  { value: "technical", label: "Technical" },
  { value: "sentiment", label: "Sentiment" },
];

const LTPI_CATEGORIES = [
  { value: "technical_btc", label: "Technical BTC" },
  { value: "on_chain", label: "On-Chain" },
];

const SOURCE_OPTIONS = [
  { value: "own_research", label: "Own Research" },
  { value: "reference_sheet", label: "Reference Sheet" },
];

export function IndicatorForm({ mode, defaultValues, onSubmit, onCancel, isLoading }: Props) {
  const { register, handleSubmit, watch, control } = useForm<AnyFormData>({
    defaultValues: defaultValues as AnyFormData,
  });

  const isValuation = mode === "valuation";

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-5"
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-zinc-200">
          {defaultValues ? "Edit" : "Add"} {isValuation ? "Valuation" : "Trend"} Indicator
        </h4>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Row 1: Name + Category */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <FieldLabel required>Indicator Name</FieldLabel>
          <Input
            placeholder="e.g. MVRV Z-Score"
            {...register("name", { required: true })}
          />
        </div>
        <div>
          <FieldLabel required>Category</FieldLabel>
          {isValuation ? (
            <Select options={SDCA_CATEGORIES} {...register("category", { required: true })} />
          ) : (
            <Select options={LTPI_CATEGORIES} {...register("category", { required: true })} />
          )}
        </div>
      </div>

      {/* Row 2: Source URL + Source Website */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <FieldLabel required>Source URL</FieldLabel>
          <Input
            type="url"
            placeholder="https://..."
            {...register("source_url", { required: true })}
          />
        </div>
        <div>
          <FieldLabel required>Source Website</FieldLabel>
          <Input
            placeholder="e.g. lookintobitcoin.com"
            {...register("source_website", { required: true })}
          />
        </div>
      </div>

      {/* ── SDCA-specific fields ──────────────────────────────────────── */}
      {isValuation && (
        <>
          {/* Row 3: Author + Source Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel>Author (TradingView)</FieldLabel>
              <Input
                placeholder="Optional"
                {...register("source_author")}
              />
            </div>
            <div>
              <FieldLabel required>Provided By</FieldLabel>
              <Select options={SOURCE_OPTIONS} {...register("provided_by", { required: true })} />
            </div>
          </div>

          {/* Z-Score slider */}
          <div>
            <FieldLabel required>Z-Score</FieldLabel>
            <Controller
              name={"z_score"}
              control={control}
              defaultValue={0}
              rules={{ required: true }}
              render={({ field }) => (
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min={-4}
                    max={4}
                    step={0.1}
                    value={field.value ?? 0}
                    onChange={(e) => field.onChange(parseFloat(e.target.value))}
                    className="flex-1 h-2 rounded-full appearance-none bg-gradient-to-r from-emerald-600 via-zinc-600 to-red-600 cursor-pointer"
                  />
                  <span className="w-14 text-right font-mono text-sm text-zinc-200">
                    {(field.value ?? 0).toFixed(1)}
                  </span>
                </div>
              )}
            />
            <div className="flex justify-between text-[10px] text-zinc-600 mt-1">
              <span>Extreme Buy (−4)</span>
              <span>Fair Value (0)</span>
              <span>Extreme Sell (+4)</span>
            </div>
          </div>

          {/* Date Updated */}
          <div className="max-w-xs">
            <FieldLabel required>Date Updated</FieldLabel>
            <Input
              type="date"
              {...register("date_updated", { required: true })}
              defaultValue={new Date().toISOString().split("T")[0]}
            />
          </div>

          {/* Comments */}
          <div className="space-y-3">
            <p className="text-xs text-zinc-500 font-medium">
              Research Documentation <span className="text-zinc-600">(min 50 chars each)</span>
            </p>
            <div>
              <FieldLabel required>Why Chosen</FieldLabel>
              <Textarea
                placeholder="Pros, cons, long-term vs short-term suitability, decay status…"
                {...register("why_chosen", { required: true, minLength: 50 })}
              />
            </div>
            <div>
              <FieldLabel required>How It Works</FieldLabel>
              <Textarea
                placeholder="Calculation logic, normalization method, timeframe, settings…"
                {...register("how_it_works", { required: true, minLength: 50 })}
              />
            </div>
            <div>
              <FieldLabel required>Scoring Logic</FieldLabel>
              <Textarea
                placeholder="Positive/negative thresholds, ±2SD values, decay adjustments…"
                {...register("scoring_logic", { required: true, minLength: 50 })}
              />
            </div>
          </div>

          {/* Decay + flags */}
          <div className="flex flex-wrap gap-6 items-start">
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" {...register("has_decay")} className="rounded border-zinc-600" />
              Has Decay
            </label>
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" {...register("is_logarithmic")} className="rounded border-zinc-600" />
              Logarithmic
            </label>
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" {...register("is_normalized")} className="rounded border-zinc-600" />
              Normalized
            </label>
          </div>
          {watch("has_decay") && (
            <div>
              <FieldLabel required>Decay Description</FieldLabel>
              <Textarea
                placeholder="Describe the decay pattern and how to account for it…"
                {...register("decay_description", { required: true })}
              />
            </div>
          )}
        </>
      )}

      {/* ── LTPI-specific fields ──────────────────────────────────────── */}
      {!isValuation && (
        <>
          {/* Author + Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel required>Author</FieldLabel>
              <Input
                placeholder="TradingView author or data source"
                {...register("author", { required: true })}
              />
            </div>
            <div>
              <FieldLabel required>Indicator Type</FieldLabel>
              <Input
                placeholder="e.g. supertrend, mvrv, rsi"
                {...register("indicator_type", { required: true })}
              />
            </div>
          </div>

          {/* Score selector */}
          <div>
            <FieldLabel required>Score</FieldLabel>
            <Controller
              name={"score"}
              control={control}
              defaultValue={0}
              rules={{ required: true }}
              render={({ field }) => (
                <div className="flex gap-2">
                  {[
                    { value: -1, label: "−1 Bearish", color: "border-red-500 bg-red-500/10 text-red-400" },
                    { value: 0, label: "0 Neutral", color: "border-zinc-600 bg-zinc-800 text-zinc-400" },
                    { value: 1, label: "+1 Bullish", color: "border-emerald-500 bg-emerald-500/10 text-emerald-400" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => field.onChange(opt.value)}
                      className={cn(
                        "flex-1 rounded-lg border py-2.5 text-sm font-medium transition-all",
                        field.value === opt.value
                          ? cn(opt.color, "ring-1 ring-offset-1 ring-offset-zinc-950", opt.value === -1 ? "ring-red-500" : opt.value === 1 ? "ring-emerald-500" : "ring-zinc-500")
                          : "border-zinc-700 bg-zinc-900 text-zinc-500 hover:text-zinc-300"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            />
          </div>

          {/* Scoring criteria + comment */}
          <div>
            <FieldLabel required>Scoring Criteria</FieldLabel>
            <Input
              placeholder="When +1, when -1, when 0"
              {...register("scoring_criteria", { required: true, minLength: 10 })}
            />
          </div>
          <div>
            <FieldLabel required>Comment</FieldLabel>
            <Textarea
              placeholder="How it works, why it's chosen (min 30 chars)…"
              {...register("comment", { required: true, minLength: 30 })}
            />
          </div>

          {/* Repaints warning */}
          <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
            <span className="text-amber-400 text-xs">⚠</span>
            <p className="text-xs text-amber-400">
              Repainting indicators are automatically rejected. Only add indicators that do not repaint.
            </p>
          </div>
        </>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2 border-t border-zinc-800">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800 transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isLoading}
          className={cn(
            "rounded-lg px-5 py-2 text-sm font-medium transition-colors",
            "bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {isLoading ? "Saving…" : defaultValues ? "Update Indicator" : "Add Indicator"}
        </button>
      </div>
    </form>
  );
}
