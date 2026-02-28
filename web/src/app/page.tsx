"use client";

import { useAccount } from "wagmi";
import { ConnectWallet } from "@/components/connect-wallet";
import { TierBadge } from "@/components/tier-badge";

const ASSETS = [
  { key: "btc", name: "Bitcoin", symbol: "BTC", icon: "₿" },
  { key: "eth", name: "Ethereum", symbol: "ETH", icon: "Ξ" },
  { key: "gold", name: "Gold", symbol: "XAU", icon: "🥇" },
  { key: "spx", name: "S&P 500", symbol: "SPX", icon: "📈" },
];

export default function Home() {
  const { isConnected } = useAccount();

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">Strategy Builder AI</h1>
            <span className="text-xs text-zinc-500 font-mono">v0.1.0</span>
          </div>
          <div className="flex items-center gap-4">
            {isConnected && <TierBadge tier="explorer" />}
            <ConnectWallet />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">
        {!isConnected ? (
          /* Landing */
          <div className="text-center py-20 space-y-6">
            <h2 className="text-4xl font-bold">
              Quantitative Allocation Signals
            </h2>
            <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
              Multi-asset signalling system powered by z-score valuation (SDCA)
              and long-term trend identification (LTPI). Built for BTC, ETH,
              Gold &amp; SPX.
            </p>
            <div className="flex justify-center gap-3 pt-4">
              <ConnectWallet />
            </div>

            {/* Feature grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 text-left">
              <FeatureCard
                title="Level 1 — SDCA"
                description="15-indicator z-score valuation system. Fundamental, technical & sentiment signals with outlier-robust scoring."
              />
              <FeatureCard
                title="Level 2 — LTPI"
                description="Long-term trend position index. 12 technical BTC + 5 on-chain indicators with binary scoring."
              />
              <FeatureCard
                title="Combined Signal Matrix"
                description="7-level allocation signals from Strongest Buy to Strongest Sell, combining valuation + trend."
              />
            </div>
          </div>
        ) : (
          /* Dashboard */
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Dashboard</h2>
              <button className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors">
                + New System
              </button>
            </div>

            {/* Asset cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {ASSETS.map((asset) => (
                <div
                  key={asset.key}
                  className="rounded-xl bg-zinc-900 p-5 hover:bg-zinc-800/80 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{asset.icon}</span>
                    <div>
                      <h3 className="font-semibold">{asset.name}</h3>
                      <p className="text-xs text-zinc-500">{asset.symbol}</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">SDCA Z-Score</span>
                      <span className="text-zinc-300">—</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">LTPI Trend</span>
                      <span className="text-zinc-300">—</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Signal</span>
                      <span className="text-zinc-400 text-xs">Not computed</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Placeholder for systems list */}
            <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-8 text-center">
              <p className="text-zinc-500">
                No indicator systems configured yet. Create your first SDCA or
                LTPI system to start receiving signals.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-zinc-600">
          <span>Strategy Builder AI — Open Source Engine</span>
          <span>Subscriptions via USDC on Base L2</span>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6">
      <h3 className="font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-zinc-400 leading-relaxed">{description}</p>
    </div>
  );
}
