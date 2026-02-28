"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
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

export default function SignalsPage() {
  const { token } = useAuth();
  const [systems, setSystems] = useState<api.SystemData[]>([]);
  const [allSignals, setAllSignals] = useState<api.Signal[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api
      .listSystems(token)
      .then(async (sys) => {
        setSystems(sys);
        const signals: api.Signal[] = [];
        for (const s of sys) {
          try {
            const hist = await api.getSignalHistory(token, s.id, 10);
            signals.push(...hist);
          } catch {
            // System may not have any signals
          }
        }
        signals.sort(
          (a, b) =>
            new Date(b.computed_at).getTime() -
            new Date(a.computed_at).getTime()
        );
        setAllSignals(signals);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  const filtered =
    filter === "all"
      ? allSignals
      : allSignals.filter((s) => s.asset === filter);

  const uniqueAssets = [...new Set(allSignals.map((s) => s.asset))];

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold">Signal Feed</h1>

      {/* Filters */}
      <div className="flex gap-2">
        <FilterBtn
          active={filter === "all"}
          onClick={() => setFilter("all")}
          label="All"
        />
        {uniqueAssets.map((a) => (
          <FilterBtn
            key={a}
            active={filter === a}
            onClick={() => setFilter(a)}
            label={a.toUpperCase()}
          />
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl bg-zinc-900 animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-12 text-center">
          <p className="text-zinc-500">No signals yet. Compute a signal from one of your systems.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((sig) => {
            const strength = sig.signal_strength ?? "hold";
            return (
              <div
                key={sig.id}
                className="rounded-xl bg-zinc-900 border border-zinc-800 p-4 flex items-start gap-4"
              >
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-zinc-500 uppercase tracking-wider font-medium">
                      {sig.asset}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-semibold",
                        SIGNAL_COLORS[strength]
                      )}
                    >
                      {SIGNAL_LABELS[strength] ?? strength}
                    </span>
                  </div>
                  <div className="flex gap-6 text-sm">
                    {sig.valuation_score != null && (
                      <span className="text-zinc-400">
                        Valuation: <span className="text-white">{sig.valuation_score.toFixed(2)}</span>
                      </span>
                    )}
                    {sig.trend_score != null && (
                      <span className="text-zinc-400">
                        Trend: <span className="text-white">{(sig.trend_score * 100).toFixed(0)}%</span>
                      </span>
                    )}
                    {sig.allocation_pct != null && (
                      <span className="text-zinc-400">
                        Alloc: <span className="text-white">{(sig.allocation_pct * 100).toFixed(0)}%</span>
                      </span>
                    )}
                  </div>
                  {sig.reasoning && (
                    <p className="text-xs text-zinc-500 line-clamp-2">{sig.reasoning}</p>
                  )}
                </div>
                <p className="text-[10px] text-zinc-600 whitespace-nowrap">
                  {new Date(sig.computed_at).toLocaleString()}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function FilterBtn({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-3 py-1 rounded-full text-xs font-medium transition-colors",
        active
          ? "bg-blue-600 text-white"
          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
      )}
    >
      {label}
    </button>
  );
}
