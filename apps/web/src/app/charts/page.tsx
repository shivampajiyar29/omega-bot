"use client";
import { useEffect, useRef, useState } from "react";
import { useOHLCV, useWatchlist } from "@/hooks/useApi";

const TIMEFRAMES = ["1m","5m","15m","30m","1h","4h","1d"];
const INDICATORS_LIST = ["EMA 9", "EMA 21", "EMA 50", "SMA 200", "RSI 14", "MACD", "BB 20", "VWAP"];

// Compute EMA
function ema(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [];
  let prev = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = 0; i < period - 1; i++) result.push(NaN);
  result.push(prev);
  for (let i = period; i < data.length; i++) {
    prev = data[i] * k + prev * (1 - k);
    result.push(prev);
  }
  return result;
}

export default function ChartsPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);

  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("15m");
  const [activeIndicators, setActiveIndicators] = useState<string[]>(["EMA 9", "EMA 21"]);
  const { data: watchlist } = useWatchlist();
  const watchlistSymbols = (watchlist?.symbols ?? [])
    .map((s) => s.symbol.toUpperCase())
    .filter((s) => s.endsWith("USDT"));
  const symbols = Array.from(new Set(["BTCUSDT", "ETHUSDT", ...watchlistSymbols]));
  const exchange = "BINANCE";
  const { data: ohlcv = [], isLoading, error } = useOHLCV(symbol, exchange, timeframe, true);
  const bars: Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }> = ohlcv.map((b: any) => ({
    time: Math.floor(new Date(b.t).getTime() / 1000),
    open: b.o,
    high: b.h,
    low: b.l,
    close: b.c,
    volume: b.v,
  }));
  const [currentBar, setCurrentBar] = useState<any>(null);

  // Lightweight-charts is loaded via dynamic import to avoid SSR issues
  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    let chart: any;

    (async () => {
      const { createChart, CrosshairMode, ColorType } = await import("lightweight-charts");

      chart = createChart(containerRef.current!, {
        layout: {
          background: { type: ColorType.Solid, color: "#16191f" },
          textColor: "#8b90a0",
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.04)" },
          horzLines: { color: "rgba(255,255,255,0.04)" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: {
          borderColor: "rgba(255,255,255,0.1)",
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        timeScale: {
          borderColor: "rgba(255,255,255,0.1)",
          timeVisible: true,
          secondsVisible: false,
        },
        width: containerRef.current!.clientWidth,
        height: 380,
      });

      chartRef.current = chart;

      // Candlestick series
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#00d4a0", downColor: "#ff4757",
        borderUpColor: "#00d4a0", borderDownColor: "#ff4757",
        wickUpColor: "#00d4a0", wickDownColor: "#ff4757",
      });
      candleSeriesRef.current = candleSeries;
      candleSeries.setData(bars);

      // Volume histogram
      const volSeries = chart.addHistogramSeries({
        color: "rgba(74,158,255,0.3)",
        priceFormat: { type: "volume" },
        priceScaleId: "",
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volSeries.setData(bars.map(b => ({
        time: b.time,
        value: b.volume,
        color: b.close >= b.open ? "rgba(0,212,160,0.25)" : "rgba(255,71,87,0.25)",
      })));

      // EMA overlays
      const closes = bars.map(b => b.close);
      const ema9  = ema(closes, 9);
      const ema21 = ema(closes, 21);

      if (activeIndicators.includes("EMA 9")) {
        const s = chart.addLineSeries({ color: "#4a9eff", lineWidth: 1.5, title: "EMA 9" });
        s.setData(bars.map((b, i) => ({ time: b.time, value: ema9[i] })).filter(p => !isNaN(p.value)));
      }
      if (activeIndicators.includes("EMA 21")) {
        const s = chart.addLineSeries({ color: "#ffb347", lineWidth: 1.5, title: "EMA 21" });
        s.setData(bars.map((b, i) => ({ time: b.time, value: ema21[i] })).filter(p => !isNaN(p.value)));
      }

      // Crosshair move handler
      chart.subscribeCrosshairMove((param: any) => {
        if (!param.time) return;
        const data = param.seriesData?.get(candleSeries);
        if (data) setCurrentBar(data as any);
      });

      // Fit content
      chart.timeScale().fitContent();

      // Resize observer
      const ro = new ResizeObserver(() => {
        chart.applyOptions({ width: containerRef.current!.clientWidth });
      });
      ro.observe(containerRef.current!);

      return () => { ro.disconnect(); };
    })();

    return () => { chart?.remove(); };
  }, [symbol, timeframe, activeIndicators.join(",")]);

  const toggleIndicator = (ind: string) => {
    setActiveIndicators(a => a.includes(ind) ? a.filter(i => i !== ind) : [...a, ind]);
  };

  const safeBar = currentBar ?? bars[bars.length - 1];
  const isUp = safeBar ? safeBar.close >= safeBar.open : true;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 0 12px" }}>
        {/* Symbol picker */}
        <select
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          style={{ background: "var(--bg2)", border: "1px solid var(--border2)", borderRadius: 6, padding: "6px 10px", color: "var(--text)", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, outline: "none", cursor: "pointer" }}
        >
          {(symbols.length ? symbols : ["BTCUSDT"]).map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        {/* Timeframe tabs */}
        <div style={{ display: "flex", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 6, padding: 3, gap: 2 }}>
          {TIMEFRAMES.map(tf => (
            <button key={tf} onClick={() => setTimeframe(tf)} style={{
              padding: "4px 10px", borderRadius: 4, border: "none", cursor: "pointer",
              fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
              background: timeframe === tf ? "var(--bg3)" : "transparent",
              color: timeframe === tf ? "var(--text)" : "var(--text3)",
            }}>{tf}</button>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        {/* OHLCV badge */}
        <div style={{ display: "flex", gap: 10, fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>
          <span style={{ color: "var(--text3)" }}>O</span><span>{safeBar?.open?.toFixed(2)}</span>
          <span style={{ color: "var(--text3)" }}>H</span><span style={{ color: "var(--green)" }}>{safeBar?.high?.toFixed(2)}</span>
          <span style={{ color: "var(--text3)" }}>L</span><span style={{ color: "var(--red)" }}>{safeBar?.low?.toFixed(2)}</span>
          <span style={{ color: "var(--text3)" }}>C</span><span style={{ color: isUp ? "var(--green)" : "var(--red)", fontWeight: 600 }}>{safeBar?.close?.toFixed(2)}</span>
        </div>
      </div>
      {isLoading && <div style={{ marginBottom: 8, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && <div style={{ marginBottom: 8, color: "var(--red)", fontSize: 12 }}>Failed to load chart data</div>}

      {/* ── Indicator toggles ────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
        {INDICATORS_LIST.map(ind => (
          <button
            key={ind}
            onClick={() => toggleIndicator(ind)}
            style={{
              padding: "3px 10px", borderRadius: 4, cursor: "pointer",
              fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
              background: activeIndicators.includes(ind) ? "rgba(74,158,255,0.12)" : "var(--bg3)",
              border: `1px solid ${activeIndicators.includes(ind) ? "rgba(74,158,255,0.3)" : "var(--border)"}`,
              color: activeIndicators.includes(ind) ? "var(--blue)" : "var(--text3)",
              transition: "all 0.1s",
            }}
          >
            {ind}
          </button>
        ))}
      </div>

      {/* ── Chart canvas ─────────────────────────────────────────────────── */}
      <div
        style={{
          background: "var(--bg2)", border: "1px solid var(--border)",
          borderRadius: 10, overflow: "hidden",
        }}
      >
        <div ref={containerRef} style={{ width: "100%" }} />
      </div>

      {/* ── Quick actions ─────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button style={{ padding: "8px 20px", background: "rgba(0,212,160,0.12)", border: "1px solid rgba(0,212,160,0.3)", borderRadius: 6, color: "var(--green)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
          ▲ BUY {symbol}
        </button>
        <button style={{ padding: "8px 20px", background: "rgba(255,71,87,0.12)", border: "1px solid rgba(255,71,87,0.3)", borderRadius: 6, color: "var(--red)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
          ▼ SELL {symbol}
        </button>
        <button style={{ padding: "8px 18px", background: "rgba(155,143,255,0.08)", border: "1px solid rgba(155,143,255,0.2)", borderRadius: 6, color: "var(--purple)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>
          ⟁ Apply Strategy
        </button>
        <button style={{ padding: "8px 18px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>
          ↺ Run Backtest
        </button>
      </div>
    </div>
  );
}
