"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { TierCard } from "@/components/tier-badge";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-3xl space-y-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Profile */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Profile</h2>
        <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5 space-y-3">
          <Row label="Wallet" value={user.wallet_address} mono />
          {user.ens_name && <Row label="ENS" value={user.ens_name} />}
          <Row label="Tier" value={user.tier.charAt(0).toUpperCase() + user.tier.slice(1)} />
          <Row
            label="Subscription"
            value={
              user.subscription_expires_at
                ? `Active until ${new Date(user.subscription_expires_at).toLocaleDateString()}`
                : user.tier === "explorer"
                ? "Free — no expiry"
                : "Inactive"
            }
          />
          <Row label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
          <Row
            label="Allowed assets"
            value={user.allowed_assets.map((a) => a.toUpperCase()).join(", ")}
          />
        </div>
      </section>

      {/* Subscription */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Subscription</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <TierCard
            tier="explorer"
            price="Free"
            current={user.tier === "explorer"}
          />
          <TierCard
            tier="strategist"
            price="29 USDC/mo"
            current={user.tier === "strategist"}
          />
          <TierCard
            tier="quant"
            price="99 USDC/mo"
            current={user.tier === "quant"}
          />
        </div>
        <p className="text-xs text-zinc-500">
          Payments are processed on Base L2 via USDC. Subscription management
          coming soon.
        </p>
      </section>

      {/* Actions */}
      <section>
        <button
          onClick={logout}
          className="px-4 py-2 rounded-lg bg-zinc-800 text-zinc-300 text-sm hover:bg-zinc-700 transition-colors"
        >
          Sign Out
        </button>
      </section>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className={mono ? "text-zinc-300 font-mono text-xs" : "text-white"}>
        {value}
      </span>
    </div>
  );
}
