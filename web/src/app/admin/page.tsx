"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import * as api from "@/lib/api";

export default function AdminOverviewPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState<api.PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api
      .getPlatformStats(token)
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-24 rounded-xl bg-zinc-900 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!stats) {
    return <p className="text-zinc-500">Failed to load platform stats.</p>;
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Platform Overview</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Users" value={String(stats.total_users)} />
        <StatCard label="Total Systems" value={String(stats.total_systems)} />
        <StatCard label="Total Signals" value={String(stats.total_signals)} />
        <StatCard
          label="Signals (24h)"
          value={String(stats.signals_last_24h)}
        />
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-4">Users by Tier</h2>
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(stats.users_by_tier).map(([tier, count]) => (
            <div
              key={tier}
              className="rounded-xl bg-zinc-900 border border-zinc-800 p-4"
            >
              <p className="text-xs text-zinc-500 capitalize mb-1">{tier}</p>
              <p className="text-2xl font-bold">{count}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-4">
      <p className="text-xs text-zinc-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
