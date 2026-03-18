import { NextRequest, NextResponse } from "next/server";

/* ───────────────────────────────────────────────────────────────────────────
 * GET /api/prices?ticker=BTC-USD&range=1y&interval=1d
 *
 * Server-side proxy to Yahoo Finance chart API. Avoids CORS issues.
 * Supports any Yahoo Finance ticker: BTC-USD, ETH-USD, AAPL, GC=F, etc.
 * ─────────────────────────────────────────────────────────────────────────── */

const VALID_RANGES = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"];
const VALID_INTERVALS = ["1d", "1wk", "1mo"];

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const ticker = searchParams.get("ticker")?.trim().toUpperCase();
  const range = searchParams.get("range") || "1y";
  const interval = searchParams.get("interval") || "1d";

  if (!ticker || ticker.length > 20 || !/^[A-Z0-9.=^-]+$/.test(ticker)) {
    return NextResponse.json(
      { error: "Invalid ticker symbol" },
      { status: 400 }
    );
  }
  if (!VALID_RANGES.includes(range)) {
    return NextResponse.json({ error: "Invalid range" }, { status: 400 });
  }
  if (!VALID_INTERVALS.includes(interval)) {
    return NextResponse.json({ error: "Invalid interval" }, { status: 400 });
  }

  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=${range}&interval=${interval}&includePrePost=false`;

  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
      signal: AbortSignal.timeout(10_000),
    });

    if (!resp.ok) {
      return NextResponse.json(
        { error: `Yahoo Finance returned ${resp.status}` },
        { status: 502 }
      );
    }

    const data = await resp.json();
    const result = data?.chart?.result?.[0];
    if (!result) {
      return NextResponse.json(
        { error: "No data found for this ticker" },
        { status: 404 }
      );
    }

    const timestamps: number[] = result.timestamp ?? [];
    const quote = result.indicators?.quote?.[0];
    if (!quote || timestamps.length === 0) {
      return NextResponse.json(
        { error: "No price data available" },
        { status: 404 }
      );
    }

    const rows = [];
    for (let i = 0; i < timestamps.length; i++) {
      const close = quote.close?.[i];
      if (close == null || isNaN(close)) continue;
      rows.push({
        date: new Date(timestamps[i] * 1000).toISOString().split("T")[0],
        open: quote.open?.[i] ?? close,
        high: quote.high?.[i] ?? close,
        low: quote.low?.[i] ?? close,
        close,
        volume: quote.volume?.[i] ?? 0,
      });
    }

    const meta = result.meta ?? {};
    return NextResponse.json({
      ticker: meta.symbol ?? ticker,
      currency: meta.currency ?? "USD",
      exchange: meta.exchangeName ?? "",
      rows,
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to fetch price data";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
