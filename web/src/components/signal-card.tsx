import type { Signal } from "@/lib/api";

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

export function SignalCard({ signal }: { signal: Signal }) {
  const strength = signal.signal_strength || "hold";
  const color = SIGNAL_COLORS[strength] || SIGNAL_COLORS.hold;
  const label = SIGNAL_LABELS[strength] || strength;

  return (
    <div className="rounded-xl bg-zinc-900 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          {signal.asset.toUpperCase()}
        </h3>
        <span className={`px-3 py-1 text-sm font-semibold rounded-full ${color}`}>
          {label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {signal.valuation_score != null && (
          <div>
            <p className="text-xs text-zinc-500">Valuation</p>
            <p className="text-xl font-bold text-white">
              {signal.valuation_score.toFixed(2)}
            </p>
          </div>
        )}
        {signal.trend_score != null && (
          <div>
            <p className="text-xs text-zinc-500">Trend</p>
            <p className="text-xl font-bold text-white">
              {(signal.trend_score * 100).toFixed(0)}%
            </p>
          </div>
        )}
        {signal.allocation_pct != null && (
          <div>
            <p className="text-xs text-zinc-500">Allocation</p>
            <p className="text-xl font-bold text-white">
              {(signal.allocation_pct * 100).toFixed(0)}%
            </p>
          </div>
        )}
      </div>

      {signal.reasoning && (
        <p className="text-sm text-zinc-400 leading-relaxed">
          {signal.reasoning}
        </p>
      )}

      <p className="text-xs text-zinc-600">
        {new Date(signal.computed_at).toLocaleString()}
      </p>
    </div>
  );
}
