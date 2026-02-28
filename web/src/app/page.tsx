"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAccount } from "wagmi";
import { ConnectWallet } from "@/components/connect-wallet";
import { useAuth } from "@/components/auth/auth-provider";

export default function Home() {
  const { isConnected } = useAccount();
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  // Auto-redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, router]);

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
            {isConnected && (
              <a
                href="/dashboard"
                className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                Dashboard →
              </a>
            )}
            <ConnectWallet />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Hero */}
        <div className="text-center py-20 space-y-6">
          <h2 className="text-4xl font-bold">
            Build Smarter Allocation Strategies
          </h2>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
            Compose multi-indicator signal systems, compute real-time
            allocations, and manage your portfolio across BTC, ETH,
            Gold &amp; S&amp;P 500.
          </p>
          <div className="flex justify-center gap-3 pt-4">
            <ConnectWallet />
          </div>

          {/* Feature grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 text-left">
            <FeatureCard
              title="Build Systems"
              description="Create custom indicator systems combining valuation, trend, and momentum signals with a guided step-by-step wizard."
            />
            <FeatureCard
              title="Real-Time Signals"
              description="Compute allocation signals on demand with outlier-robust scoring and automatic decay detection."
            />
            <FeatureCard
              title="Portfolio View"
              description="See combined 7-level allocation recommendations across all your tracked assets in one dashboard."
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-zinc-600">
          <span>Strategy Builder AI</span>
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
