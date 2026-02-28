"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/utils";
import * as api from "@/lib/api";

export default function SystemsPage() {
  const { token } = useAuth();
  const [systems, setSystems] = useState<api.SystemData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api
      .listSystems(token)
      .then(setSystems)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your Systems</h1>
        <Link
          href="/dashboard/systems/new"
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors"
        >
          + New System
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl bg-zinc-900 animate-pulse"
            />
          ))}
        </div>
      ) : systems.length === 0 ? (
        <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-12 text-center">
          <h3 className="font-semibold text-lg mb-2">No systems yet</h3>
          <p className="text-zinc-500 mb-4">
            Create your first indicator system to start generating signals.
          </p>
          <Link
            href="/dashboard/systems/new"
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition-colors inline-block"
          >
            Create System
          </Link>
        </div>
      ) : (
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50">
                <th className="text-left px-4 py-3 text-zinc-400 font-medium">Name</th>
                <th className="text-left px-4 py-3 text-zinc-400 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-zinc-400 font-medium">Asset</th>
                <th className="text-left px-4 py-3 text-zinc-400 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-zinc-400 font-medium">Created</th>
                <th className="text-right px-4 py-3 text-zinc-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {systems.map((sys) => (
                <tr
                  key={sys.id}
                  className="border-b border-zinc-800/50 hover:bg-zinc-900/30 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/systems/${sys.id}`}
                      className="font-medium text-white hover:text-blue-400 transition-colors"
                    >
                      {sys.name}
                    </Link>
                    {sys.description && (
                      <p className="text-xs text-zinc-500 mt-0.5 truncate max-w-xs">
                        {sys.description}
                      </p>
                    )}
                  </td>
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
                    {new Date(sys.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/dashboard/systems/${sys.id}`}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
