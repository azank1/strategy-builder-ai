"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { TierBadge } from "@/components/tier-badge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import * as api from "@/lib/api";

export default function AdminUsersPage() {
  const { token } = useAuth();
  const [data, setData] = useState<api.AdminUsersResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const fetchUsers = (p: number) => {
    if (!token) return;
    setLoading(true);
    api
      .getAdminUsers(token, p)
      .then((res) => {
        setData(res);
        setPage(p);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers(1);
  }, [token]);

  const handleTierChange = async (
    userId: string,
    newTier: string
  ) => {
    if (!token) return;
    try {
      await api.updateUserTier(token, userId, newTier);
      toast.success(`Tier updated to ${newTier}`);
      fetchUsers(page);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update tier"
      );
    }
  };

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Users</h1>
        {data && (
          <span className="text-sm text-zinc-500">
            {data.total} total users
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-14 rounded-xl bg-zinc-900 animate-pulse"
            />
          ))}
        </div>
      ) : !data || data.users.length === 0 ? (
        <p className="text-zinc-500">No users found.</p>
      ) : (
        <>
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Wallet
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Tier
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Systems
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Signals
                  </th>
                  <th className="text-left px-4 py-3 text-zinc-400 font-medium">
                    Joined
                  </th>
                  <th className="text-right px-4 py-3 text-zinc-400 font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-zinc-800/50 hover:bg-zinc-900/30"
                  >
                    <td className="px-4 py-3 font-mono text-xs">
                      {u.wallet_address.slice(0, 8)}...
                      {u.wallet_address.slice(-6)}
                      {u.ens_name && (
                        <span className="ml-2 text-zinc-500">{u.ens_name}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <TierBadge
                        tier={
                          u.tier as "explorer" | "strategist" | "quant"
                        }
                      />
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {u.system_count}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {u.signal_count}
                    </td>
                    <td className="px-4 py-3 text-zinc-500 text-xs">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <select
                        value={u.tier}
                        onChange={(e) =>
                          handleTierChange(u.id, e.target.value)
                        }
                        className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs text-white"
                      >
                        <option value="explorer">Explorer</option>
                        <option value="strategist">Strategist</option>
                        <option value="quant">Quant</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => fetchUsers(page - 1)}
                disabled={page <= 1}
                className="px-3 py-1 rounded bg-zinc-800 text-sm disabled:opacity-40"
              >
                ← Prev
              </button>
              <span className="text-sm text-zinc-500">
                Page {page} / {totalPages}
              </span>
              <button
                onClick={() => fetchUsers(page + 1)}
                disabled={page >= totalPages}
                className="px-3 py-1 rounded bg-zinc-800 text-sm disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
