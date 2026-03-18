"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { TradeChart } from "./trade-chart";
import { EquityChart } from "./equity-chart";
import { MetricsTable } from "./metrics-table";
import {
  parseCSV,
  computeEquityCurve,
  computeMetrics,
  type PriceRow,
  type Trade,
} from "./engine";

/* ───────────────────────────────────────────────────────────────────────────
 * CSVBacktester — Main orchestrator for the CSV-to-backtest workflow.
 *
 *  1. Search ticker OR upload CSV (drag-and-drop or file picker)
 *  2. View price chart, click to place BUY / SELL markers
 *  3. Equity curve + metrics update in real-time (no save button)
 *  4. Trade log with individual delete
 * ─────────────────────────────────────────────────────────────────────────── */

const INITIAL_CAPITAL = 10_000;

const QUICK_TICKERS = [
  { label: "BTC", ticker: "BTC-USD" },
  { label: "ETH", ticker: "ETH-USD" },
  { label: "SOL", ticker: "SOL-USD" },
  { label: "GOLD", ticker: "GC=F" },
  { label: "S&P 500", ticker: "^GSPC" },
  { label: "AAPL", ticker: "AAPL" },
];

const RANGES = [
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "2Y", value: "2y" },
  { label: "5Y", value: "5y" },
  { label: "Max", value: "max" },
];

const INTERVALS = [
  { label: "Daily", value: "1d" },
  { label: "Weekly", value: "1wk" },
  { label: "Monthly", value: "1mo" },
];

export function CSVBacktester() {
  const [priceData, setPriceData] = useState<PriceRow[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [tradeMode, setTradeMode] = useState<"buy" | "sell">("buy");
  const [dataSource, setDataSource] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [tickerInput, setTickerInput] = useState("");
  const [range, setRange] = useState("1y");
  const [interval, setInterval] = useState("1d");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch ticker from API ──
  const fetchTicker = useCallback(
    async (ticker: string) => {
      if (!ticker.trim()) return;
      setLoading(true);
      setParseError(null);
      setTrades([]);

      try {
        const resp = await fetch(
          `/api/prices?ticker=${encodeURIComponent(ticker.trim())}&range=${range}&interval=${interval}`
        );
        const data = await resp.json();

        if (!resp.ok) {
          setParseError(data.error || "Failed to fetch price data");
          setLoading(false);
          return;
        }

        if (!data.rows || data.rows.length === 0) {
          setParseError("No price data returned for this ticker");
          setLoading(false);
          return;
        }

        const rows: PriceRow[] = data.rows.map(
          (r: { date: string; open: number; high: number; low: number; close: number; volume: number }, i: number) => ({
            index: i,
            date: r.date,
            open: r.open,
            high: r.high,
            low: r.low,
            close: r.close,
            volume: r.volume,
          })
        );

        setPriceData(rows);
        setDataSource(`${data.ticker} · ${data.exchange || "Yahoo"}`);
      } catch {
        setParseError("Network error — could not fetch price data");
      } finally {
        setLoading(false);
      }
    },
    [range, interval]
  );

  // ── CSV file handler ──
  const handleFile = useCallback((file: File) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setParseError("Please upload a .csv file");
      return;
    }
    setParseError(null);
    setDataSource(file.name);
    setTrades([]);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const data = parseCSV(text);
      if (data.length === 0) {
        setParseError(
          'Could not parse CSV. Ensure it has "Date" and "Close" columns.'
        );
        return;
      }
      setPriceData(data);
    };
    reader.readAsText(file);
  }, []);

  // ── Chart click → add/remove trade ──
  const handleChartClick = useCallback(
    (index: number, date: string, price: number) => {
      setTrades((prev) => {
        const existing = prev.find((t) => t.index === index);
        if (existing) {
          // Toggle off if clicking the same spot
          return prev.filter((t) => t.index !== index);
        }
        return [
          ...prev,
          {
            id: crypto.randomUUID(),
            index,
            date,
            price,
            type: tradeMode,
          },
        ];
      });
    },
    [tradeMode]
  );

  const removeTrade = useCallback((id: string) => {
    setTrades((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearTrades = useCallback(() => setTrades([]), []);
  const undoTrade = useCallback(() => setTrades((prev) => prev.slice(0, -1)), []);

  // ── Real-time computations ──
  const { equity, ispZones } = useMemo(
    () => computeEquityCurve(priceData, trades, INITIAL_CAPITAL),
    [priceData, trades]
  );

  const metrics = useMemo(
    () => computeMetrics(equity, trades, INITIAL_CAPITAL),
    [equity, trades]
  );

  const sortedTrades = useMemo(
    () => [...trades].sort((a, b) => a.index - b.index),
    [trades]
  );

  // ── Drop handlers ──
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const resetAll = useCallback(() => {
    setPriceData([]);
    setTrades([]);
    setDataSource(null);
    setParseError(null);
    setTickerInput("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // ── Render ──

  // Upload / ticker search screen
  if (priceData.length === 0) {
    return (
      <div className="space-y-6">
        {/* Ticker search */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-4">
          <h3 className="text-sm font-medium text-zinc-300">
            Search Ticker
          </h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === "Enter") fetchTicker(tickerInput);
              }}
              placeholder="BTC-USD, ETH-USD, AAPL, GC=F ..."
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none transition-colors"
            />
            <button
              onClick={() => fetchTicker(tickerInput)}
              disabled={loading || !tickerInput.trim()}
              className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Loading..." : "Load"}
            </button>
          </div>

          {/* Range + interval selectors */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Range:</span>
              <div className="flex rounded-lg border border-zinc-700 overflow-hidden">
                {RANGES.map((r) => (
                  <button
                    key={r.value}
                    onClick={() => setRange(r.value)}
                    className={cn(
                      "px-2.5 py-1 text-xs font-medium transition-colors",
                      range === r.value
                        ? "bg-zinc-700 text-white"
                        : "bg-zinc-800/50 text-zinc-500 hover:text-zinc-300"
                    )}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">Interval:</span>
              <div className="flex rounded-lg border border-zinc-700 overflow-hidden">
                {INTERVALS.map((iv) => (
                  <button
                    key={iv.value}
                    onClick={() => setInterval(iv.value)}
                    className={cn(
                      "px-2.5 py-1 text-xs font-medium transition-colors",
                      interval === iv.value
                        ? "bg-zinc-700 text-white"
                        : "bg-zinc-800/50 text-zinc-500 hover:text-zinc-300"
                    )}
                  >
                    {iv.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Quick tickers */}
          <div className="flex flex-wrap gap-2">
            {QUICK_TICKERS.map((t) => (
              <button
                key={t.ticker}
                onClick={() => {
                  setTickerInput(t.ticker);
                  fetchTicker(t.ticker);
                }}
                disabled={loading}
                className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-1.5 text-xs text-zinc-400 hover:text-white hover:border-zinc-500 disabled:opacity-40 transition-colors"
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="flex-1 border-t border-zinc-800" />
          <span className="text-xs text-zinc-600">or upload CSV</span>
          <div className="flex-1 border-t border-zinc-800" />
        </div>

        {/* CSV upload */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 cursor-pointer transition-colors",
            dragOver
              ? "border-blue-500 bg-blue-500/5"
              : "border-zinc-700 bg-zinc-900/50 hover:border-zinc-500"
          )}
        >
          <p className="text-sm text-zinc-400">
            Drop a CSV file here, or{" "}
            <span className="text-blue-400 underline">browse</span>
          </p>
          <p className="text-xs text-zinc-600">
            Expects columns: Date, Close (Open, High, Low, Volume optional)
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>

        {parseError && (
          <p className="text-xs text-red-400 text-center">{parseError}</p>
        )}
      </div>
    );
  }

  // Main backtester UI
  return (
    <div className="space-y-6">
      {/* ── Toolbar ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-zinc-900/50 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-500 font-mono">{dataSource}</span>
          <span className="text-xs text-zinc-600">·</span>
          <span className="text-xs text-zinc-500">
            {priceData.length.toLocaleString()} candles
          </span>
          <span className="text-xs text-zinc-600">·</span>
          <span className="text-xs text-zinc-500">
            {trades.length} markers
          </span>
          {trades.length >= 80 && (
            <span className="text-[10px] text-amber-500/70">
              {trades.length >= 100 ? "100+ trades placed" : `${100 - trades.length} to 100`}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* BUY / SELL mode toggle */}
          <div className="flex rounded-lg border border-zinc-700 overflow-hidden">
            <button
              onClick={() => setTradeMode("buy")}
              className={cn(
                "px-3 py-1.5 text-xs font-medium transition-colors",
                tradeMode === "buy"
                  ? "bg-emerald-600 text-white"
                  : "bg-zinc-800 text-zinc-400 hover:text-white"
              )}
            >
              ▲ BUY
            </button>
            <button
              onClick={() => setTradeMode("sell")}
              className={cn(
                "px-3 py-1.5 text-xs font-medium transition-colors",
                tradeMode === "sell"
                  ? "bg-red-600 text-white"
                  : "bg-zinc-800 text-zinc-400 hover:text-white"
              )}
            >
              ▼ SELL
            </button>
          </div>

          <button
            onClick={undoTrade}
            disabled={trades.length === 0}
            className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Undo
          </button>
          <button
            onClick={clearTrades}
            disabled={trades.length === 0}
            className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Clear All
          </button>
          <button
            onClick={resetAll}
            className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
          >
            New Chart
          </button>
        </div>
      </div>

      {/* ── Price Chart ── */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-zinc-300">
            Price Chart — Click to place trades
          </h3>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-[10px] text-zinc-500">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
              ISP Zone
            </span>
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full font-medium",
                tradeMode === "buy"
                  ? "bg-emerald-900/50 text-emerald-400"
                  : "bg-red-900/50 text-red-400"
              )}
            >
              Mode: {tradeMode.toUpperCase()}
            </span>
          </div>
        </div>
        <TradeChart
          priceData={priceData}
          trades={trades}
          ispZones={ispZones}
          onCandleClick={handleChartClick}
          tradeMode={tradeMode}
        />
      </div>

      {/* ── Equity Curve ── */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-zinc-300">Equity Curve</h3>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-[10px] text-zinc-500">
              <span className="inline-block w-3 border-t border-dashed border-zinc-500" />
              Buy &amp; Hold
            </span>
            {equity.length > 0 && (
              <span
                className={cn(
                  "text-xs font-mono",
                  metrics.totalReturn >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                )}
              >
                {metrics.totalReturn >= 0 ? "+" : ""}
                {metrics.totalReturn.toFixed(2)}%
              </span>
            )}
          </div>
        </div>
        <EquityChart equityCurve={equity} initialCapital={INITIAL_CAPITAL} />
      </div>

      {/* ── Metrics ── */}
      <MetricsTable metrics={metrics} initialCapital={INITIAL_CAPITAL} />

      {/* ── Trade Log ── */}
      {sortedTrades.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <h3 className="text-sm font-medium text-zinc-300 mb-3">
            Trade Log ({sortedTrades.length} markers ·{" "}
            {metrics.completedTrades} round-trips)
          </h3>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-2 px-2">#</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-left py-2 px-2">Date</th>
                  <th className="text-right py-2 px-2">Price</th>
                  <th className="text-right py-2 px-2" />
                </tr>
              </thead>
              <tbody>
                {sortedTrades.map((trade, i) => (
                  <tr
                    key={trade.id}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                  >
                    <td className="py-1.5 px-2 text-zinc-500">{i + 1}</td>
                    <td className="py-1.5 px-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium",
                          trade.type === "buy"
                            ? "bg-emerald-900/40 text-emerald-400"
                            : "bg-red-900/40 text-red-400"
                        )}
                      >
                        {trade.type === "buy" ? "▲" : "▼"}{" "}
                        {trade.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-zinc-400 font-mono">
                      {trade.date}
                    </td>
                    <td className="py-1.5 px-2 text-right text-zinc-300 font-mono">
                      {trade.price.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="py-1.5 px-2 text-right">
                      <button
                        onClick={() => removeTrade(trade.id)}
                        className="text-zinc-600 hover:text-red-400 transition-colors"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
