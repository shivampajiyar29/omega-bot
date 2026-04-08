"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export interface OHLCV {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface CandlestickChartProps {
  data: OHLCV[];
  height?: number;
  showVolume?: boolean;
  showEMA?: { period: number; color: string }[];
  onCrosshairMove?: (bar: OHLCV | null) => void;
}

function computeEMA(data: OHLCV[], period: number): { time: number; value: number }[] {
  if (data.length < period) return [];
  const k = 2 / (period + 1);
  const closes = data.map(d => d.close);
  let prev = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
  const out: { time: number; value: number }[] = [];
  for (let i = period - 1; i < data.length; i++) {
    if (i === period - 1) { out.push({ time: data[i].time, value: prev }); continue; }
    prev = closes[i] * k + prev * (1 - k);
    out.push({ time: data[i].time, value: prev });
  }
  return out;
}

export function CandlestickChart({
  data,
  height = 380,
  showVolume = true,
  showEMA = [],
  onCrosshairMove,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

  const initChart = useCallback(async () => {
    if (!containerRef.current || !data.length) return;

    const { createChart, CrosshairMode, ColorType, LineStyle } = await import("lightweight-charts");
    type UTCTimestamp = import("lightweight-charts").UTCTimestamp;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
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
        scaleMargins: { top: 0.1, bottom: showVolume ? 0.3 : 0.05 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
      width:  containerRef.current.clientWidth,
      height,
    });

    chartRef.current = chart;

    // Candles
    const candles = chart.addCandlestickSeries({
      upColor:        "#00d4a0",
      downColor:      "#ff4757",
      borderUpColor:  "#00d4a0",
      borderDownColor:"#ff4757",
      wickUpColor:    "#00d4a0",
      wickDownColor:  "#ff4757",
    });
    candles.setData(
      data.map((b) => ({
        time: b.time as UTCTimestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );
    candleRef.current = candles;

    // Volume
    if (showVolume) {
      const vol = chart.addHistogramSeries({
        priceFormat:   { type: "volume" },
        priceScaleId:  "",
      });
      vol.setData(data.map(b => ({
        time:  b.time as UTCTimestamp,
        value: b.volume ?? 0,
        color: b.close >= b.open ? "rgba(0,212,160,0.25)" : "rgba(255,71,87,0.25)",
      })));
    }

    // EMA overlays
    for (const { period, color } of showEMA) {
      const emaData = computeEMA(data, period);
      if (emaData.length) {
        const line = chart.addLineSeries({ color, lineWidth: 2, title: `EMA ${period}`, priceLineVisible: false });
        line.setData(emaData.map((p) => ({ ...p, time: p.time as UTCTimestamp })));
      }
    }

    // Crosshair
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove((param: any) => {
        if (!param.time) { onCrosshairMove(null); return; }
        const d = param.seriesData?.get(candles);
        onCrosshairMove(d ? (d as OHLCV) : null);
      });
    }

    chart.timeScale().fitContent();

    // Resize
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);
    setReady(true);

    return () => { ro.disconnect(); };
  }, [data, height, showVolume, showEMA, onCrosshairMove]);

  useEffect(() => {
    initChart();
    return () => { chartRef.current?.remove(); };
  }, [initChart]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%", height,
        background: "#16191f",
        borderRadius: 8, overflow: "hidden",
        position: "relative",
      }}
    >
      {!ready && (
        <div style={{
          position: "absolute", inset: 0, display: "flex",
          alignItems: "center", justifyContent: "center",
          color: "var(--text3)", fontSize: 12,
        }}>
          Loading chart…
        </div>
      )}
    </div>
  );
}
