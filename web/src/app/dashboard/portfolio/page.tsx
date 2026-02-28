"use client";

import { useState } from "react";
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

export default function PortfolioPage() {
  const { token, user } = useAuth();
  const [portfolio, setPortfolio] = useState<api.PortfolioResponse | null>(
    null
  );
  const [computing, setComputing] = useState(false);

  const isEligible =
    user?.tier === "strategist" || user?.tier === "quant";

  const handleCompute = async () => {
    if (!token) return;
    setComputing(true);
    try {
      const res = await api.computePortfolio(token);
      setPortfolio(res);
      toast.success("Portfolio computed");
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Portfolio compute failed"
      );
    } finally {
      setComputing(false);
    }
  };

  if (!isEligible) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 space-y-4">
        <h1 className="text-2xl font-bold">Portfolio View</h1>
        <p className="text-zinc-400">
          Portfolio analysis is available for Strategist and Quant subscribers.
        </p>
        <a
          href="/dashboard/settings"
          className="inline-block px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors"
        >
          Upgrade Plan
        </a>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <button
          onClick={handleCompute}
          disabled={computing}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors disabled:opacity-50"
        >
          {computing ? "Computing..." : "Compute Portfolio"}
        </button>
      </div>

      {!portfolio ? (
        <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-12 text-center">
          <p className="text-zinc-500">
            Click "Compute Portfolio" to generate a combined portfolio signal
            across all your active systems.
          </p>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <SummaryCard
              label="Total Allocation"
              value={`${(portfolio.total_allocation * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Systems"
              value={String(portfolio.signals.length)}
            />
            <SummaryCard
              label="Computed"
              value={new Date(portfolio.computed_at).toLocaleTimeString()}
            />
          </div>

          {/* Per-asset signals */}
          <div className="space-y-3">
            {portfolio.signals.map((sig) => {
              const strength = sig.signal_strength ?? "hold";
              return (
                <div
                  key={sig.id}
                  className="rounded-xl bg-zinc-900 border border-zinc-800 p-5 flex items-center gap-6"
                >
                  <div className="text-center min-w-[60px]">
                    <p className="text-xs text-zinc-500 uppercase">
                      {sig.asset}
                    </p>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-semibold mt-1 inline-block",
                        SIGNAL_COLORS[strength]
                      )}
                    >
                      {SIGNAL_LABELS[strength]}
                    </span>
                  </div>
                  <div className="flex-1 grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-zinc-500 text-xs">Valuation</p>
                      <p className="font-bold">
                        {sig.valuation_score?.toFixed(2) ?? "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-zinc-500 text-xs">Trend</p>
                      <p className="font-bold">
                        {sig.trend_score != null
                          ? `${(sig.trend_score * 100).toFixed(0)}%`
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-zinc-500 text-xs">Allocation</p>
                      <p className="font-bold">
                        {sig.allocation_pct != null
                          ? `${(sig.allocation_pct * 100).toFixed(0)}%`
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-4">
      <p className="text-xs text-zinc-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
