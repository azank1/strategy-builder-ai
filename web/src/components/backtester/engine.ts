/* ───────────────────────────────────────────────────────────────────────────
 * Backtester Engine — CSV parsing, equity computation, performance metrics
 *
 * All calculations are pure functions for use with React useMemo.
 * ─────────────────────────────────────────────────────────────────────────── */

// ─── Types ──────────────────────────────────────────────────────────────────

export interface PriceRow {
  index: number;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Trade {
  id: string;
  index: number; // index into priceData array
  date: string;
  price: number;
  type: "buy" | "sell";
}

export interface EquityPoint {
  date: string;
  equity: number;
  drawdown: number;
  buyAndHold: number;
}

export interface ISPZone {
  startDate: string;
  endDate: string;
}

export interface BacktestMetrics {
  totalReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  sortinoRatio: number;
  omegaRatio: number;
  winRate: number;
  completedTrades: number;
  avgTradeReturn: number;
  profitFactor: number;
}

// ─── CSV Parsing ────────────────────────────────────────────────────────────

const DATE_HEADERS = ["date", "datetime", "time", "timestamp", "date/time"];
const CLOSE_HEADERS = ["close", "adj close", "adj_close", "price", "last", "close/last"];

export function parseCSV(text: string): PriceRow[] {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];

  const headers = lines[0]
    .split(",")
    .map((h) => h.trim().toLowerCase().replace(/"/g, ""));

  const dateIdx = headers.findIndex((h) => DATE_HEADERS.includes(h));
  const closeIdx = headers.findIndex((h) => CLOSE_HEADERS.includes(h));
  const openIdx = headers.findIndex((h) => h === "open");
  const highIdx = headers.findIndex((h) => h === "high");
  const lowIdx = headers.findIndex((h) => h === "low");
  const volIdx = headers.findIndex((h) => ["volume", "vol"].includes(h));

  if (dateIdx === -1 || closeIdx === -1) return [];

  const rows: PriceRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",").map((c) => c.trim().replace(/"/g, ""));
    if (cols.length <= Math.max(dateIdx, closeIdx)) continue;

    const close = parseFloat(cols[closeIdx]);
    if (isNaN(close) || close <= 0) continue;

    rows.push({
      index: rows.length,
      date: cols[dateIdx],
      open: openIdx >= 0 ? parseFloat(cols[openIdx]) || close : close,
      high: highIdx >= 0 ? parseFloat(cols[highIdx]) || close : close,
      low: lowIdx >= 0 ? parseFloat(cols[lowIdx]) || close : close,
      close,
      volume: volIdx >= 0 ? parseFloat(cols[volIdx]) || 0 : 0,
    });
  }

  return rows;
}

// ─── Equity Curve Computation ───────────────────────────────────────────────

export function computeEquityCurve(
  priceData: PriceRow[],
  trades: Trade[],
  initialCapital: number
): { equity: EquityPoint[]; ispZones: ISPZone[] } {
  if (priceData.length === 0) return { equity: [], ispZones: [] };

  const tradeMap = new Map<number, Trade>();
  for (const t of [...trades].sort((a, b) => a.index - b.index)) {
    tradeMap.set(t.index, t);
  }

  const equity: EquityPoint[] = [];
  const ispZones: ISPZone[] = [];
  let capital = initialCapital;
  let position = 0;
  let inPosition = false;
  let peak = initialCapital;
  let entryDate: string | null = null;
  const firstPrice = priceData[0].close;

  for (let i = 0; i < priceData.length; i++) {
    const row = priceData[i];
    const trade = tradeMap.get(i);

    if (trade) {
      if (trade.type === "buy" && !inPosition) {
        position = capital / row.close;
        capital = 0;
        inPosition = true;
        entryDate = row.date;
      } else if (trade.type === "sell" && inPosition) {
        capital = position * row.close;
        position = 0;
        inPosition = false;
        if (entryDate) {
          ispZones.push({ startDate: entryDate, endDate: row.date });
          entryDate = null;
        }
      }
    }

    const currentEquity = capital + position * row.close;
    peak = Math.max(peak, currentEquity);
    const drawdown = peak > 0 ? ((currentEquity - peak) / peak) * 100 : 0;
    const buyAndHold = initialCapital * (row.close / firstPrice);

    equity.push({
      date: row.date,
      equity: Math.round(currentEquity * 100) / 100,
      drawdown: Math.round(drawdown * 100) / 100,
      buyAndHold: Math.round(buyAndHold * 100) / 100,
    });
  }

  // If still in position, close the final ISP zone at end of data
  if (inPosition && entryDate) {
    ispZones.push({
      startDate: entryDate,
      endDate: priceData[priceData.length - 1].date,
    });
  }

  return { equity, ispZones };
}

// ─── Performance Metrics ────────────────────────────────────────────────────

const EMPTY_METRICS: BacktestMetrics = {
  totalReturn: 0,
  maxDrawdown: 0,
  sharpeRatio: 0,
  sortinoRatio: 0,
  omegaRatio: 0,
  winRate: 0,
  completedTrades: 0,
  avgTradeReturn: 0,
  profitFactor: 0,
};

export function computeMetrics(
  equityCurve: EquityPoint[],
  trades: Trade[],
  initialCapital: number
): BacktestMetrics {
  if (equityCurve.length < 2 || trades.length === 0) return { ...EMPTY_METRICS };

  // ── Daily returns from equity curve ──
  const returns: number[] = [];
  for (let i = 1; i < equityCurve.length; i++) {
    const prev = equityCurve[i - 1].equity;
    if (prev > 0) {
      returns.push((equityCurve[i].equity - prev) / prev);
    }
  }

  if (returns.length === 0) return { ...EMPTY_METRICS };

  const finalEquity = equityCurve[equityCurve.length - 1].equity;
  const totalReturn = ((finalEquity - initialCapital) / initialCapital) * 100;
  const maxDrawdown = Math.min(...equityCurve.map((e) => e.drawdown));

  // ── Sharpe Ratio (annualised, risk-free = 0) ──
  const n = returns.length;
  const meanReturn = returns.reduce((s, r) => s + r, 0) / n;
  const variance = returns.reduce((s, r) => s + (r - meanReturn) ** 2, 0) / n;
  const stdReturn = Math.sqrt(variance);
  const sharpeRatio = stdReturn > 0 ? (meanReturn / stdReturn) * Math.sqrt(252) : 0;

  // ── Sortino Ratio (annualised, MAR = 0) ──
  const downsideVariance =
    returns.reduce((s, r) => s + (r < 0 ? r ** 2 : 0), 0) / n;
  const downsideDev = Math.sqrt(downsideVariance);
  const sortinoRatio =
    downsideDev > 0 ? (meanReturn / downsideDev) * Math.sqrt(252) : 0;

  // ── Omega Ratio (threshold = 0) ──
  const gains = returns
    .filter((r) => r > 0)
    .reduce((s, r) => s + r, 0);
  const losses = returns
    .filter((r) => r < 0)
    .reduce((s, r) => s + Math.abs(r), 0);
  const omegaRatio = losses > 0 ? gains / losses : gains > 0 ? 99.99 : 1;

  // ── Trade-level statistics ──
  const sorted = [...trades].sort((a, b) => a.index - b.index);
  const completed: { entry: number; exit: number }[] = [];
  let entryPrice: number | null = null;

  for (const t of sorted) {
    if (t.type === "buy" && entryPrice === null) {
      entryPrice = t.price;
    } else if (t.type === "sell" && entryPrice !== null) {
      completed.push({ entry: entryPrice, exit: t.price });
      entryPrice = null;
    }
  }

  const tradeReturns = completed.map(
    (t) => ((t.exit - t.entry) / t.entry) * 100
  );
  const winCount = tradeReturns.filter((r) => r > 0).length;
  const winRate =
    completed.length > 0 ? (winCount / completed.length) * 100 : 0;
  const avgTradeReturn =
    tradeReturns.length > 0
      ? tradeReturns.reduce((s, r) => s + r, 0) / tradeReturns.length
      : 0;

  const grossProfit = tradeReturns
    .filter((r) => r > 0)
    .reduce((s, r) => s + r, 0);
  const grossLoss = Math.abs(
    tradeReturns.filter((r) => r < 0).reduce((s, r) => s + r, 0)
  );
  const profitFactor =
    grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 99.99 : 0;

  const round2 = (v: number) => Math.round(v * 100) / 100;
  const clamp = (v: number) => Math.min(v, 99.99);

  return {
    totalReturn: round2(totalReturn),
    maxDrawdown: round2(maxDrawdown),
    sharpeRatio: round2(sharpeRatio),
    sortinoRatio: round2(sortinoRatio),
    omegaRatio: round2(clamp(omegaRatio)),
    winRate: round2(winRate),
    completedTrades: completed.length,
    avgTradeReturn: round2(avgTradeReturn),
    profitFactor: round2(clamp(profitFactor)),
  };
}
