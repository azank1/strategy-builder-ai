const TIER_CONFIG = {
  explorer: {
    label: "Explorer",
    color: "bg-zinc-700 text-zinc-300",
    description: "Free — BTC only",
  },
  strategist: {
    label: "Strategist",
    color: "bg-blue-600/20 text-blue-400 border border-blue-500/30",
    description: "BTC + ETH + Gold + SPX",
  },
  quant: {
    label: "Quant",
    color: "bg-purple-600/20 text-purple-400 border border-purple-500/30",
    description: "All assets + AI insights",
  },
} as const;

type Tier = keyof typeof TIER_CONFIG;

export function TierBadge({ tier }: { tier: Tier }) {
  const cfg = TIER_CONFIG[tier];
  return (
    <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

export function TierCard({
  tier,
  price,
  current,
  onSelect,
}: {
  tier: Tier;
  price: string;
  current: boolean;
  onSelect?: () => void;
}) {
  const cfg = TIER_CONFIG[tier];
  return (
    <div
      className={`rounded-xl p-6 ${
        current ? "ring-2 ring-blue-500 bg-zinc-900" : "bg-zinc-900/50"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-bold text-white">{cfg.label}</h3>
        <TierBadge tier={tier} />
      </div>
      <p className="text-sm text-zinc-400 mb-4">{cfg.description}</p>
      <p className="text-2xl font-bold text-white mb-4">{price}</p>
      {!current && onSelect && (
        <button
          onClick={onSelect}
          className="w-full py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
        >
          Upgrade
        </button>
      )}
      {current && (
        <div className="w-full py-2 text-center text-sm text-zinc-500">
          Current plan
        </div>
      )}
    </div>
  );
}
