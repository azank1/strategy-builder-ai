"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { ConnectWallet } from "@/components/connect-wallet";
import { TierBadge } from "@/components/tier-badge";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: "◉" },
  { href: "/dashboard/systems", label: "Systems", icon: "⚙" },
  { href: "/dashboard/signals", label: "Signals", icon: "⚡" },
  { href: "/dashboard/portfolio", label: "Portfolio", icon: "◐" },
  { href: "/dashboard/settings", label: "Settings", icon: "☰" },
];

const ADMIN_NAV = [
  { href: "/admin", label: "Admin", icon: "⛊" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, isAuthenticated, isAdmin } = useAuth();

  // Guard: redirect would be handled client-side, show loading if not authed
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-zinc-400">Connect your wallet to access the dashboard.</p>
          <ConnectWallet />
        </div>
      </div>
    );
  }

  const navItems = isAdmin ? [...NAV_ITEMS, ...ADMIN_NAV] : NAV_ITEMS;

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 border-r border-zinc-800 bg-zinc-950 flex flex-col">
        <div className="px-5 py-5 border-b border-zinc-800">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-lg font-bold">Strategy Builder AI</span>
          </Link>
          <span className="text-[10px] text-zinc-600 font-mono">v0.1.0</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  active
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                )}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-4 py-4 border-t border-zinc-800 space-y-2">
          {user && (
            <>
              <div className="flex items-center gap-2">
                <TierBadge tier={user.tier as "explorer" | "strategist" | "quant"} />
                <span className="text-xs text-zinc-500 font-mono truncate">
                  {user.wallet_address.slice(0, 6)}...{user.wallet_address.slice(-4)}
                </span>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-6">
          <div />
          <div className="flex items-center gap-4">
            {user && <TierBadge tier={user.tier as "explorer" | "strategist" | "quant"} />}
            <ConnectWallet />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
