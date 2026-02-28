"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import * as api from "@/lib/api";

const SYSTEM_TYPES = [
  {
    key: "valuation",
    label: "Valuation",
    description: "Multi-indicator valuation scoring with outlier-robust z-scores",
  },
  {
    key: "trend",
    label: "Trend",
    description: "Long-term trend detection combining technical and on-chain data",
  },
  {
    key: "momentum",
    label: "Momentum",
    description: "Medium-term momentum signals (coming soon)",
    disabled: true,
  },
  {
    key: "rotation",
    label: "Rotation",
    description: "Multi-asset class rotation signals (coming soon)",
    disabled: true,
  },
];

const ASSET_OPTIONS = [
  { key: "btc", label: "Bitcoin", symbol: "BTC", icon: "₿" },
  { key: "eth", label: "Ethereum", symbol: "ETH", icon: "Ξ" },
  { key: "gold", label: "Gold", symbol: "XAU", icon: "🥇" },
  { key: "spx", label: "S&P 500", symbol: "SPX", icon: "📈" },
];

type Step = "type" | "asset" | "details" | "review";

export default function NewSystemPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [step, setStep] = useState<Step>("type");
  const [systemType, setSystemType] = useState<string>("");
  const [asset, setAsset] = useState<string>("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async () => {
    if (!token || !systemType || !asset || !name.trim()) return;
    setSubmitting(true);
    try {
      await api.createSystem(token, {
        system_type: systemType,
        asset,
        name: name.trim(),
        description: description.trim() || undefined,
        system_data: { asset, indicators: [], date_updated: new Date().toISOString().split("T")[0] },
      });
      toast.success("System created");
      router.push("/dashboard/systems");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create system");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Create New System</h1>

      {/* Progress */}
      <div className="flex items-center gap-2 text-sm">
        {(["type", "asset", "details", "review"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <span className="text-zinc-600">→</span>}
            <span
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium",
                s === step
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-800 text-zinc-500"
              )}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </span>
          </div>
        ))}
      </div>

      {/* Step: Type */}
      {step === "type" && (
        <div className="space-y-4">
          <p className="text-zinc-400">Choose a signal type for your system.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SYSTEM_TYPES.map((t) => (
              <button
                key={t.key}
                disabled={t.disabled}
                onClick={() => {
                  setSystemType(t.key);
                  setStep("asset");
                }}
                className={cn(
                  "rounded-xl border p-4 text-left transition-colors",
                  t.disabled
                    ? "border-zinc-800 bg-zinc-900/30 text-zinc-600 cursor-not-allowed"
                    : systemType === t.key
                    ? "border-blue-500 bg-blue-600/10"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600"
                )}
              >
                <h3 className="font-semibold mb-1">{t.label}</h3>
                <p className="text-xs text-zinc-400">{t.description}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step: Asset */}
      {step === "asset" && (
        <div className="space-y-4">
          <p className="text-zinc-400">Select the asset to track.</p>
          <div className="grid grid-cols-2 gap-3">
            {ASSET_OPTIONS.map((a) => {
              const allowed = user?.allowed_assets?.includes(a.key) ?? false;
              return (
                <button
                  key={a.key}
                  disabled={!allowed}
                  onClick={() => {
                    setAsset(a.key);
                    setStep("details");
                  }}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-colors",
                    !allowed
                      ? "border-zinc-800 bg-zinc-900/30 text-zinc-600 cursor-not-allowed"
                      : asset === a.key
                      ? "border-blue-500 bg-blue-600/10"
                      : "border-zinc-800 bg-zinc-900 hover:border-zinc-600"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{a.icon}</span>
                    <div>
                      <h3 className="font-semibold">{a.label}</h3>
                      <p className="text-xs text-zinc-500">{a.symbol}</p>
                    </div>
                  </div>
                  {!allowed && (
                    <p className="text-[10px] text-zinc-600 mt-1">Upgrade required</p>
                  )}
                </button>
              );
            })}
          </div>
          <button
            onClick={() => setStep("type")}
            className="text-sm text-zinc-500 hover:text-white transition-colors"
          >
            ← Back
          </button>
        </div>
      )}

      {/* Step: Details */}
      {step === "details" && (
        <div className="space-y-4">
          <p className="text-zinc-400">Name your system.</p>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">
                System Name *
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. BTC Valuation Q1"
                className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                placeholder="What's this system tracking?"
                className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-600 focus:border-blue-500 focus:outline-none resize-none"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setStep("asset")}
              className="text-sm text-zinc-500 hover:text-white transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={() => setStep("review")}
              disabled={!name.trim()}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Review
            </button>
          </div>
        </div>
      )}

      {/* Step: Review */}
      {step === "review" && (
        <div className="space-y-4">
          <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5 space-y-3">
            <Row label="Type" value={systemType} />
            <Row label="Asset" value={asset.toUpperCase()} />
            <Row label="Name" value={name} />
            {description && <Row label="Description" value={description} />}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setStep("details")}
              className="text-sm text-zinc-500 hover:text-white transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleCreate}
              disabled={submitting}
              className="px-6 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-50"
            >
              {submitting ? "Creating..." : "Create System"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-white capitalize">{value}</span>
    </div>
  );
}
