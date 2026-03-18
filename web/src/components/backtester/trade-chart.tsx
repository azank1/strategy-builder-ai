"use client";

import { useEffect, useRef, useCallback, useMemo } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  ColorType,
  CrosshairMode,
} from "lightweight-charts";
import type { PriceRow, Trade, ISPZone } from "./engine";

/* ───────────────────────────────────────────────────────────────────────────
 * TradeChart — TradingView-style candlestick chart with click-to-trade.
 *
 * Uses lightweight-charts (TradingView open source) for real OHLC candles.
 * Click a candle → trade executes at the candle's CLOSE price.
 * BUY markers below bar (green ▲), SELL markers above (red ▼).
 * Scroll, zoom, pan — full interactive charting.
 * ─────────────────────────────────────────────────────────────────────────── */

interface Props {
  priceData: PriceRow[];
  trades: Trade[];
  ispZones: ISPZone[];
  onCandleClick: (index: number, date: string, closePrice: number) => void;
  tradeMode: "buy" | "sell";
}

export function TradeChart({
  priceData,
  trades,
  ispZones,
  onCandleClick,
  tradeMode,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const priceDataRef = useRef(priceData);
  const onCandleClickRef = useRef(onCandleClick);

  // Keep refs current so the subscribeClick callback sees latest data
  useEffect(() => { priceDataRef.current = priceData; }, [priceData]);
  useEffect(() => { onCandleClickRef.current = onCandleClick; }, [onCandleClick]);

  // Convert price data to lightweight-charts format
  const candleData = useMemo(
    () =>
      priceData.map((p) => ({
        time: p.date as Time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      })),
    [priceData]
  );

  // Build marker list from trades
  const markers = useMemo<SeriesMarker<Time>[]>(() => {
    return [...trades]
      .sort((a, b) => a.index - b.index)
      .map((t) => ({
        time: t.date as Time,
        position: t.type === "buy" ? ("belowBar" as const) : ("aboveBar" as const),
        color: t.type === "buy" ? "#10b981" : "#ef4444",
        shape: t.type === "buy" ? ("arrowUp" as const) : ("arrowDown" as const),
        text: `${t.type === "buy" ? "BUY" : "SELL"} @ ${t.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
        size: 1.5,
      }));
  }, [trades]);

  // Create chart once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 480,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a",
        fontFamily: "var(--font-geist-mono), monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1e1e22" },
        horzLines: { color: "#1e1e22" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#52525b80", style: 2, width: 1, labelBackgroundColor: "#27272a" },
        horzLine: { color: "#52525b80", style: 2, width: 1, labelBackgroundColor: "#27272a" },
      },
      rightPriceScale: {
        borderColor: "#27272a",
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: {
        borderColor: "#27272a",
        timeVisible: false,
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b98190",
      wickDownColor: "#ef444490",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    // Create markers plugin
    markersRef.current = createSeriesMarkers(series, []);

    // Click a candle → trade at close price
    chart.subscribeClick((param) => {
      if (!param.time) return;
      const timeStr = String(param.time);
      const match = priceDataRef.current.find((p) => p.date === timeStr);
      if (match) {
        onCandleClickRef.current(match.index, match.date, match.close);
      }
    });

    // Responsive resize
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      markersRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update crosshair color when trade mode changes
  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.applyOptions({
      crosshair: {
        vertLine: {
          color: tradeMode === "buy" ? "#10b98160" : "#ef444460",
          labelBackgroundColor: tradeMode === "buy" ? "#065f46" : "#7f1d1d",
        },
      },
    });
  }, [tradeMode]);

  // Update candle data when price data changes
  useEffect(() => {
    if (!seriesRef.current || candleData.length === 0) return;
    seriesRef.current.setData(candleData);
    chartRef.current?.timeScale().fitContent();
  }, [candleData]);

  // Update markers (buy/sell arrows) when trades change
  useEffect(() => {
    if (!markersRef.current) return;
    markersRef.current.setMarkers(markers);
  }, [markers]);

  if (priceData.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className="w-full rounded-lg overflow-hidden"
      style={{ height: 480 }}
    />
  );
}
