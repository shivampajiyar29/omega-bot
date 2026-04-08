"use client";
import { useEffect, useRef, useCallback, useState } from "react";

type Tick = {
  symbol: string;
  exchange: string;
  price: number;
  bid?: number;
  ask?: number;
  volume?: number;
  timestamp: string;
};

type UseMarketFeedOptions = {
  symbols: string[];
  onTick?: (tick: Tick) => void;
  enabled?: boolean;
};

/**
 * useMarketFeed
 * Subscribes to the OmegaBot WebSocket market data feed.
 * Falls back to mock price simulation if WS is unavailable.
 */
export function useMarketFeed({ symbols, onTick, enabled = true }: UseMarketFeedOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [prices, setPrices] = useState<Record<string, number>>({});
  const retriesRef = useRef(0);
  const maxRetries = 3;

  const connect = useCallback(() => {
    if (!enabled || symbols.length === 0) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsUrl = (process.env.NEXT_PUBLIC_WS_URL ?? apiBase.replace(/^http/, "ws")).replace(
      /^http/,
      "ws"
    );
    const wsPath = "/api/v1/ws/market";

    try {
      const ws = new WebSocket(`${wsUrl}${wsPath}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retriesRef.current = 0;
        ws.send(JSON.stringify({ action: "subscribe", symbols }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "tick") {
            setPrices(p => ({ ...p, [msg.symbol]: msg.price }));
            onTick?.(msg as Tick);
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Retry with backoff
        if (retriesRef.current < maxRetries) {
          retriesRef.current++;
          const delay = Math.pow(2, retriesRef.current) * 1000;
          setTimeout(connect, delay);
        } else {
          // Fall back to mock simulation
          startMockFeed();
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket not available — use mock
      startMockFeed();
    }
  }, [symbols, enabled, onTick]);

  // Mock price feed fallback (for development / when API is down)
  const mockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mockPricesRef = useRef<Record<string, number>>({
    RELIANCE: 2847.30, TCS: 3912.60, INFY: 1834.90,
    HDFC: 1672.15, NIFTY50: 24832.15, BTCUSDT: 87432.00,
  });

  const startMockFeed = useCallback(() => {
    if (mockIntervalRef.current) return;
    mockIntervalRef.current = setInterval(() => {
      for (const sym of symbols) {
        const base = mockPricesRef.current[sym] ?? 1000;
        const newPrice = +(base * (1 + (Math.random() - 0.5) * 0.002)).toFixed(2);
        mockPricesRef.current[sym] = newPrice;
        setPrices(p => ({ ...p, [sym]: newPrice }));
        onTick?.({
          symbol: sym,
          exchange: "MOCK",
          price: newPrice,
          timestamp: new Date().toISOString(),
        });
      }
    }, 1500);
  }, [symbols, onTick]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (mockIntervalRef.current) clearInterval(mockIntervalRef.current);
    };
  }, [connect]);

  const subscribe = useCallback((newSymbols: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "subscribe", symbols: newSymbols }));
    }
  }, []);

  const unsubscribe = useCallback((removeSymbols: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "unsubscribe", symbols: removeSymbols }));
    }
  }, []);

  return { prices, connected, subscribe, unsubscribe };
}

/**
 * useBotFeed
 * Subscribes to live bot status and P&L updates.
 */
export function useBotFeed(enabled = true) {
  const wsRef = useRef<WebSocket | null>(null);
  const [botStatuses, setBotStatuses] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    if (!enabled) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsUrl = (process.env.NEXT_PUBLIC_WS_URL ?? apiBase.replace(/^http/, "ws")).replace(
      /^http/,
      "ws"
    );
    const wsPath = "/api/v1/ws/bots";

    try {
      const ws = new WebSocket(`${wsUrl}${wsPath}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "bot_update") {
            setBotStatuses(msg.bots);
          }
        } catch {
          // ignore
        }
      };
    } catch {
      // WS unavailable
    }

    return () => wsRef.current?.close();
  }, [enabled]);

  return { botStatuses };
}
