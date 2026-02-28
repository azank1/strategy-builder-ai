"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import * as api from "@/lib/api";

const SIGNAL_COLORS: Record<string, string> = {
  strongest_buy: "text-emerald-400 bg-emerald-500/10",
  cautious_buy: "text-green-400 bg-green-500/10",
  light_buy: "text-lime-400 bg-lime-500/10",
  hold: "text-zinc-400 bg-zinc-500/10",
  reduce: "text-amber-400 bg-amber-500/10",
  partial_profit: "text-orange-400 bg-orange-500/10",
  strongest_sell: "text-red-400 bg-red-500/10",
};

const SIGNAL_LABELS: Record<string, string> = {
  strongest_buy: "Strongest Buy",
  cautious_buy: "Cautious Buy",
  light_buy: "Light Buy",
  hold: "Hold",
  reduce: "Reduce",
  partial_profit: "Partial Profit",
  strongest_sell: "Strongest Sell",
};

export default function SystemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { token } = useAuth();

  const [system, setSystem] = useState<api.SystemData | null>(null);
  const [history, setHistory] = useState<api.Signal[]>([]);
  const [computing, setComputing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token || !id) return;
    setLoading(true);
    Promise.all([
      api.listSystems(token).then((sys) => sys.find((s) => s.id === id) ?? null),
      api.getSignalHistory(token, id, 30).catch(() => []),
    ])
      .then(([sys, hist]) => {
        setSystem(sys);
        setHistory(hist);
      })
      .finally(() => setLoading(false));
  }, [token, id]);

  const handleCompute = async () => {
    if (!token || !id) return;
    setComputing(true);
    try {
      const sig = await api.computeSignal(token, id);
      setHistory((prev) => [sig, ...prev]);
      toast.success("Signal computed");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Compute failed");
    } finally {
      setComputing(false);
    }
  };

  const handleToggleActive = async () => {
    if (!token || !system) return;
    try {
      const updated = await api.updateSystem(token, system.id, {
        is_active: !system.is_active,
      });
      setSystem(updated);
      toast.success(updated.is_active ? "System activated" : "System paused");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleDelete = async () => {
    if (!token || !system) return;
    if (!confirm("Delete this system? This cannot be undone.")) return;
    try {
      await api.deleteSystem(token, system.id);
      toast.success("System deleted");
      router.push("/dashboard/systems");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl space-y-4">
        <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
        <div className="h-40 bg-zinc-900 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!system) {
    return (
      <div className="text-center py-12">
        <p className="text-zinc-500">System not found.</p>
      </div>
    );
  }

  const latestSignal = history[0] ?? null;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{system.name}</h1>
          <p className="text-sm text-zinc-500 mt-1">
            <span className="capitalize">{system.system_type}</span> ·{" "}
            <span className="uppercase">{system.asset}</span>
            {system.description && <> · {system.description}</>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCompute}
            disabled={computing}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-50"
          >
            {computing ? "Computing..." : "Compute Signal"}
          </button>
          <button
            onClick={handleToggleActive}
            className={cn(
              "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              system.is_active
                ? "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                : "bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30"
            )}
          >
            {system.is_active ? "Pause" : "Activate"}
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-2 rounded-lg bg-red-600/10 text-red-400 text-sm hover:bg-red-600/20 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Latest signal summary */}
      {latestSignal && (
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-zinc-500 mb-1">Signal</p>
            <span
              className={cn(
                "px-2 py-0.5 rounded-full text-xs font-semibold",
                SIGNAL_COLORS[latestSignal.signal_strength ?? "hold"]
              )}
            >
              {SIGNAL_LABELS[latestSignal.signal_strength ?? "hold"] ?? "—"}
            </span>
          </div>
          {latestSignal.valuation_score != null && (
            <div>
              <p className="text-xs text-zinc-500 mb-1">Valuation</p>
              <p className="text-lg font-bold">
                {latestSignal.valuation_score.toFixed(2)}
              </p>
            </div>
          )}
          {latestSignal.trend_score != null && (
            <div>
              <p className="text-xs text-zinc-500 mb-1">Trend</p>
              <p className="text-lg font-bold">
                {(latestSignal.trend_score * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {latestSignal.allocation_pct != null && (
            <div>
              <p className="text-xs text-zinc-500 mb-1">Allocation</p>
              <p className="text-lg font-bold">
                {(latestSignal.allocation_pct * 100).toFixed(0)}%
              </p>
            </div>
          )}
        </div>
      )}

      {/* Signal history */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Signal History</h2>
        {history.length === 0 ? (
          <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-8 text-center">
            <p className="text-zinc-500">
              No signals computed yet. Click "Compute Signal" to generate one.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">Signal</th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">Valuation</th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">Trend</th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">Allocation</th>
                </tr>
              </thead>
              <tbody>
                {history.map((sig) => (
                  <tr
                    key={sig.id}
                    className="border-b border-zinc-800/50 hover:bg-zinc-900/30"
                  >
                    <td className="px-4 py-3 text-zinc-400 text-xs">
                      {new Date(sig.computed_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-full text-xs font-medium",
                          SIGNAL_COLORS[sig.signal_strength ?? "hold"]
                        )}
                      >
                        {SIGNAL_LABELS[sig.signal_strength ?? "hold"] ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {sig.valuation_score?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {sig.trend_score != null
                        ? `${(sig.trend_score * 100).toFixed(0)}%`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {sig.allocation_pct != null
                        ? `${(sig.allocation_pct * 100).toFixed(0)}%`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
