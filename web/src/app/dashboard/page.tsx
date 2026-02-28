"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { TierBadge } from "@/components/tier-badge";
import { cn } from "@/lib/utils";
import * as api from "@/lib/api";

const ASSETS = [
  { key: "btc", name: "Bitcoin", symbol: "BTC", icon: "₿" },
  { key: "eth", name: "Ethereum", symbol: "ETH", icon: "Ξ" },
  { key: "gold", name: "Gold", symbol: "XAU", icon: "🥇" },
  { key: "spx", name: "S&P 500", symbol: "SPX", icon: "📈" },
];

const SIGNAL_COLORS: Record<string, string> = {
  strongest_buy: "text-emerald-400",
  cautious_buy: "text-green-400",
  light_buy: "text-lime-400",
  hold: "text-zinc-400",
  reduce: "text-amber-400",
  partial_profit: "text-orange-400",
  strongest_sell: "text-red-400",
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

export default function DashboardPage() {
  const { token, user } = useAuth();
  const [systems, setSystems] = useState<api.SystemData[]>([]);
  const [signals, setSignals] = useState<api.Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      api.listSystems(token),
      api.getDashboardSignals(token),
    ])
      .then(([sys, sigs]) => {
        setSystems(sys);
        setSignals(sigs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  // Group signals by asset
  const signalByAsset: Record<string, api.Signal> = {};
  for (const sig of signals) {
    if (!signalByAsset[sig.asset]) {
      signalByAsset[sig.asset] = sig;
    }
  }

  const activeSystems = systems.filter((s) => s.is_active);
  const totalAllocation = signals.reduce(
    (sum, s) => sum + (s.allocation_pct ?? 0),
    0
  );

  return (
    <div className="max-w-6xl space-y-8">
      {/* Summary strip */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <SummaryCard label="Active Systems" value={String(activeSystems.length)} />
        <SummaryCard label="Assets Tracked" value={String(user?.allowed_assets?.length ?? 0)} />
        <SummaryCard
          label="Total Allocation"
          value={`${(totalAllocation * 100).toFixed(0)}%`}
        />
        <SummaryCard
          label="Tier"
          value={user?.tier ? user.tier.charAt(0).toUpperCase() + user.tier.slice(1) : "—"}
        />
      </div>

      {/* Asset grid */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Assets</h2>
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="rounded-xl bg-zinc-900 p-5 h-40 animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {ASSETS.map((asset) => {
              const sig = signalByAsset[asset.key];
              const allowed = user?.allowed_assets?.includes(asset.key);
              const strength = sig?.signal_strength ?? null;
              return (
                <div
                  key={asset.key}
                  className={cn(
                    "rounded-xl bg-zinc-900 p-5 transition-colors",
                    allowed
                      ? "hover:bg-zinc-800/80 cursor-pointer"
                      : "opacity-50 cursor-not-allowed"
                  )}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-2xl">{asset.icon}</span>
                    <div>
                      <h3 className="font-semibold">{asset.name}</h3>
                      <p className="text-xs text-zinc-500">{asset.symbol}</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Row
                      label="Valuation"
                      value={
                        sig?.valuation_score != null
                          ? sig.valuation_score.toFixed(2)
                          : "—"
                      }
                    />
                    <Row
                      label="Trend"
                      value={
                        sig?.trend_score != null
                          ? `${(sig.trend_score * 100).toFixed(0)}%`
                          : "—"
                      }
                    />
                    <Row
                      label="Signal"
                      value={
                        strength ? (
                          <span
                            className={cn(
                              "text-xs font-medium",
                              SIGNAL_COLORS[strength] ?? "text-zinc-400"
                            )}
                          >
                            {SIGNAL_LABELS[strength] ?? strength}
                          </span>
                        ) : (
                          <span className="text-zinc-500 text-xs">
                            Not computed
                          </span>
                        )
                      }
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Systems overview */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Your Systems</h2>
          <a
            href="/dashboard/systems/new"
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors"
          >
            + New System
          </a>
        </div>
        {systems.length === 0 ? (
          <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-8 text-center">
            <p className="text-zinc-500">
              No systems configured yet. Create your first system to start
              receiving signals.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Name
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Type
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Asset
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Last Signal
                  </th>
                </tr>
              </thead>
              <tbody>
                {systems.map((sys) => {
                  const sig = signals.find(
                    (s) => s.asset === sys.asset
                  );
                  return (
                    <tr
                      key={sys.id}
                      className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors"
                    >
                      <td className="px-4 py-3 font-medium">{sys.name}</td>
                      <td className="px-4 py-3 text-zinc-400 capitalize">
                        {sys.system_type}
                      </td>
                      <td className="px-4 py-3 text-zinc-400 uppercase">
                        {sys.asset}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-xs font-medium",
                            sys.is_active
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-zinc-700 text-zinc-400"
                          )}
                        >
                          {sys.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500 text-xs">
                        {sig
                          ? new Date(sig.computed_at).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Recent signals */}
      {signals.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-4">Recent Signals</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {signals.slice(0, 6).map((sig) => {
              const strength = sig.signal_strength ?? "hold";
              return (
                <div
                  key={sig.id}
                  className="rounded-xl bg-zinc-900 p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-zinc-500 uppercase tracking-wider">
                      {sig.asset}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-medium",
                        SIGNAL_COLORS[strength] ?? "text-zinc-400"
                      )}
                    >
                      {SIGNAL_LABELS[strength] ?? strength}
                    </span>
                  </div>
                  {sig.reasoning && (
                    <p className="text-xs text-zinc-400 line-clamp-2">
                      {sig.reasoning}
                    </p>
                  )}
                  <p className="text-[10px] text-zinc-600">
                    {new Date(sig.computed_at).toLocaleString()}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

// ─── Small components ────────────────────────────────────────────────────────

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-4">
      <p className="text-xs text-zinc-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-300">{value}</span>
    </div>
  );
}
