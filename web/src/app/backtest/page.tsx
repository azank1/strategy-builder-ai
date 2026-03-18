"use client";

import Link from "next/link";
import { CSVBacktester } from "@/components/backtester/csv-backtester";

export default function BacktestPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Minimal top bar */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-lg font-bold hover:opacity-80 transition-opacity">
          Strategy Builder AI
        </Link>
        <span className="text-xs text-zinc-600 font-mono">CSV Backtester</span>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">CSV Backtester</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Upload a price chart CSV, mark your entries &amp; exits to define ISP
            zones, and watch the equity curve &amp; metrics update in real-time.
          </p>
        </div>
        <CSVBacktester />
      </main>
    </div>
  );
}
