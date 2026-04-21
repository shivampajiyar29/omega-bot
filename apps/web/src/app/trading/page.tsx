"use client";
import { useState, useEffect } from "react";
import { useStore } from "@/store/useStore";
import { toast } from "sonner";
import {
  useBots, useStartBot, useStopBot, useKillAllBots,
  usePlaceOrder, useTradingPositions, useAISignals, useOrders,
} from "@/hooks/useApi";
import { useMarketFeed } from "@/hooks/useMarketFeed";

const SYMBOLS_CRYPTO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
const SYMBOLS_INDIAN = ["RELIANCE", "TCS", "INFY", "HDFC", "NIFTY50"];

export default function TradingPage() {
  const { tradingMode } = useStore();
  const isLive = tradingMode === "live";

  const [symbol, setSymbol]   = useState("BTCUSDT");
  const [qty, setQty]         = useState("0.001");
  const [price, setPrice]     = useState("");
  const [scope, setScope]     = useState<"crypto" | "indian">("crypto");

  // Real API data
  const { data: bots = [],       refetch: refetchBots }    = useBots();
  const { data: posData,         refetch: refetchPos }     = useTradingPositions();
  const { data: aiSignals = [] }                           = useAISignals();
  const { data: recentOrders = [] }                        = useOrders({ limit: 8 });

  const startBot   = useStartBot();
  const stopBot    = useStopBot();
  const killAll    = useKillAllBots();
  const placeOrder = usePlaceOrder();

  // Real-time price feed via WebSocket
  const allSymbols = [...SYMBOLS_CRYPTO, ...SYMBOLS_INDIAN];
  const { prices, connected: wsConnected } = useMarketFeed({ symbols: allSymbols });

  const currentPrice = prices[symbol] ?? 0;

  // Calculate summary from real data
  const positions      = posData?.positions ?? [];
  const runningBots    = bots.filter((b: any) => b.status === "running");
  const totalUnrealized = posData?.total_unrealized ?? 0;

  const handleBuy = async () => {
    if (!qty || parseFloat(qty) <= 0) { toast.error("Enter a valid quantity"); return; }
    const p = price ? parseFloat(price) : undefined;
    toast.loading(`Placing BUY ${qty} ${symbol}…`, { id: "order" });
    try {
      const result = await placeOrder.mutateAsync({
        symbol, side: "buy", quantity: parseFloat(qty), price: p,
      });
      if (result.success) {
        toast.success(result.message ?? `✅ BUY ${qty} ${symbol} @ ${result.fill_price?.toFixed(4)}`, { id: "order" });
      } else {
        toast.error(result.error ?? "Order failed", { id: "order" });
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Order failed", { id: "order" });
    }
  };

  const handleSell = async () => {
    if (!qty || parseFloat(qty) <= 0) { toast.error("Enter a valid quantity"); return; }
    const p = price ? parseFloat(price) : undefined;
    toast.loading(`Placing SELL ${qty} ${symbol}…`, { id: "order" });
    try {
      const result = await placeOrder.mutateAsync({
        symbol, side: "sell", quantity: parseFloat(qty), price: p,
      });
      if (result.success) {
        toast.success(result.message ?? `✅ SELL ${qty} ${symbol}`, { id: "order" });
      } else {
        toast.error(result.error ?? "Order failed — no open position?", { id: "order" });
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Order failed", { id: "order" });
    }
  };

  const handleStartBot = async (botId: string) => {
    try {
      await startBot.mutateAsync(botId);
      toast.success("Bot started");
    } catch { toast.error("Failed to start bot"); }
  };

  const handleStopBot = async (botId: string) => {
    try {
      await stopBot.mutateAsync(botId);
      toast.info("Bot stopped");
    } catch { toast.error("Failed to stop bot"); }
  };

  const handleKillAll = async () => {
    if (!confirm("Stop ALL running bots?")) return;
    try {
      const r = await killAll.mutateAsync();
      toast.warning(`Kill switch: ${(r as any).stopped ?? 0} bots stopped`);
    } catch { toast.error("Kill switch failed"); }
  };

  // Auto-fill price from live feed
  useEffect(() => {
    if (currentPrice > 0 && !price) {
      // Don't auto-fill — let user decide
    }
  }, [currentPrice]);

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>
            {isLive ? "Live Trading" : "Paper Trading"}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: wsConnected ? "var(--green)" : "var(--red)", display: "inline-block" }} />
            <span style={{ fontSize: 11, color: "var(--text3)" }}>
              {wsConnected ? "WebSocket live" : "WebSocket offline"} ·{" "}
              {aiSignals.length > 0 ? `${aiSignals.length} AI signals` : "No AI signals yet"}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ padding: "8px 16px", borderRadius: 8, fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12,
            background: isLive ? "rgba(255,71,87,0.1)" : "rgba(255,179,71,0.1)",
            border: `1px solid ${isLive ? "rgba(255,71,87,0.3)" : "rgba(255,179,71,0.3)"}`,
            color: isLive ? "var(--red)" : "var(--amber)", letterSpacing: "1px" }}>
            {isLive ? "● LIVE" : "● PAPER"}
          </div>
          {runningBots.length > 0 && (
            <button onClick={handleKillAll}
              style={{ padding: "7px 14px", background: "rgba(255,71,87,0.1)", border: "1px solid rgba(255,71,87,0.3)",
                borderRadius: 6, color: "var(--red)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
              ⊘ Kill All Bots
            </button>
          )}
        </div>
      </div>

      {/* Summary stats — REAL data */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { label: "Unrealized P&L",  value: `${totalUnrealized >= 0 ? "+" : ""}₹${totalUnrealized.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`, color: totalUnrealized >= 0 ? "var(--green)" : "var(--red)" },
          { label: "Running Bots",    value: runningBots.length.toString(),  color: "var(--blue)" },
          { label: "Open Positions",  value: positions.length.toString(),     color: "var(--text)" },
          { label: "Orders Today",    value: recentOrders.length.toString(),  color: "var(--text)" },
        ].map((s: any) => (
          <div key={s.label} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>{s.label}</div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>

        {/* LEFT — Bot Monitor + AI Signals */}
        <div>
          {/* Bot Monitor */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: 10 }}>
              Bot Monitor ({bots.length})
            </div>
            {bots.length === 0 ? (
              <div style={{ padding: 20, textAlign: "center", color: "var(--text3)", fontSize: 12, background: "var(--bg2)", border: "1px dashed var(--border)", borderRadius: 10 }}>
                No bots yet. Go to <a href="/strategy" style={{ color: "var(--blue)" }}>Strategy Builder</a> to create one.
              </div>
            ) : bots.slice(0, 4).map((b: any) => (
              <div key={b.id} style={{ background: "var(--bg2)", border: `1px solid ${b.status === "running" ? "rgba(0,212,160,0.2)" : "var(--border)"}`, borderRadius: 10, padding: "12px 14px", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", flexShrink: 0, background: b.status === "running" ? "var(--green)" : b.status === "paused" ? "var(--amber)" : "var(--text3)" }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 13 }}>{b.name}</div>
                    <div style={{ fontSize: 10, color: "var(--text3)" }}>{b.symbol} · {b.trading_mode?.toUpperCase()} · {b.status?.toUpperCase()}</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {b.status !== "running" ? (
                    <button onClick={() => handleStartBot(b.id)}
                      style={{ padding: "5px 12px", borderRadius: 5, cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, background: "rgba(0,212,160,0.1)", border: "1px solid rgba(0,212,160,0.3)", color: "var(--green)" }}>
                      ▶ Start
                    </button>
                  ) : (
                    <button onClick={() => handleStopBot(b.id)}
                      style={{ padding: "5px 12px", borderRadius: 5, cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, background: "rgba(255,179,71,0.1)", border: "1px solid rgba(255,179,71,0.3)", color: "var(--amber)" }}>
                      ⏸ Stop
                    </button>
                  )}
                </div>
              </div>
            ))}
            <a href="/strategy" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: 10, background: "transparent", border: "1px dashed var(--border2)", borderRadius: 10, color: "var(--text3)", fontSize: 12, fontFamily: "Syne, sans-serif", textDecoration: "none", marginTop: 4 }}>
              + Deploy new bot
            </a>
          </div>

          {/* AI Signals */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>
              Live AI Signals
            </div>
            {aiSignals.length === 0 ? (
              <div style={{ color: "var(--text3)", fontSize: 12, textAlign: "center", padding: 16 }}>
                Waiting for AI signals… (market stream must be running)
              </div>
            ) : aiSignals.slice(0, 6).map((sig: any) => (
              <div key={sig.symbol} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12, width: 80, flexShrink: 0 }}>{sig.symbol}</span>
                <span style={{ padding: "2px 8px", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 11,
                  background: sig.action === "buy" ? "rgba(0,212,160,0.1)" : sig.action === "sell" ? "rgba(255,71,87,0.1)" : "rgba(255,179,71,0.08)",
                  color: sig.action === "buy" ? "var(--green)" : sig.action === "sell" ? "var(--red)" : "var(--amber)" }}>
                  {sig.action?.toUpperCase()}
                </span>
                <span style={{ fontSize: 11, color: "var(--text3)", flex: 1 }}>{(sig.confidence * 100).toFixed(0)}%</span>
                <span style={{ fontSize: 10, color: "var(--text3)" }}>{sig.source}</span>
                <button onClick={() => setSymbol(sig.symbol)}
                  style={{ fontSize: 10, padding: "2px 8px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 4, cursor: "pointer", color: "var(--text3)" }}>
                  Trade
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT — Quick Order + Positions + Recent Orders */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Quick Order Panel — REAL */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>
              Quick Order
            </div>

            {/* Market selector */}
            <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
              {(["crypto", "indian"] as const).map(s => (
                <button key={s} onClick={() => { setScope(s); setSymbol(s === "crypto" ? "BTCUSDT" : "RELIANCE"); }}
                  style={{ flex: 1, padding: "5px", borderRadius: 5, border: "none", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
                    background: scope === s ? "var(--bg1)" : "var(--bg3)", color: scope === s ? "var(--text)" : "var(--text3)" }}>
                  {s === "crypto" ? "Crypto" : "Indian"}
                </button>
              ))}
            </div>

            {/* Symbol selector */}
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4 }}>Symbol</div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {(scope === "crypto" ? SYMBOLS_CRYPTO : SYMBOLS_INDIAN).map(s => (
                  <button key={s} onClick={() => setSymbol(s)}
                    style={{ padding: "4px 10px", borderRadius: 4, border: `1px solid ${symbol === s ? "var(--blue)" : "var(--border)"}`,
                      background: symbol === s ? "rgba(74,158,255,0.1)" : "var(--bg3)", cursor: "pointer",
                      fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                      color: symbol === s ? "var(--blue)" : "var(--text3)" }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Live price display */}
            {currentPrice > 0 && (
              <div style={{ padding: "8px 10px", background: "var(--bg3)", borderRadius: 6, marginBottom: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif" }}>Live Price</span>
                <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 14, color: "var(--green)" }}>
                  {scope === "indian" ? "₹" : "$"}{currentPrice.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                </span>
              </div>
            )}

            {/* Quantity */}
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4 }}>
                Quantity {currentPrice > 0 && qty ? `(≈ ${scope === "indian" ? "₹" : "$"}${(parseFloat(qty) * currentPrice).toLocaleString(undefined, { maximumFractionDigits: 2 })})` : ""}
              </div>
              <input value={qty} onChange={e => setQty(e.target.value)} type="number" placeholder={scope === "crypto" ? "0.001" : "10"}
                style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none" }} />
            </div>

            {/* Price (optional) */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4 }}>Limit Price (blank = Market)</div>
              <input value={price} onChange={e => setPrice(e.target.value)} type="number" placeholder={`Market (~${currentPrice > 0 ? currentPrice.toFixed(2) : "?"})`}
                style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none" }} />
            </div>

            {/* BUY / SELL buttons */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <button onClick={handleBuy} disabled={placeOrder.isPending}
                style={{ padding: "10px", background: "rgba(0,212,160,0.12)", border: "1px solid rgba(0,212,160,0.4)", borderRadius: 6,
                  color: "var(--green)", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 700, cursor: "pointer",
                  opacity: placeOrder.isPending ? 0.6 : 1 }}>
                {placeOrder.isPending ? "…" : "▲ BUY"}
              </button>
              <button onClick={handleSell} disabled={placeOrder.isPending}
                style={{ padding: "10px", background: "rgba(255,71,87,0.12)", border: "1px solid rgba(255,71,87,0.4)", borderRadius: 6,
                  color: "var(--red)", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 700, cursor: "pointer",
                  opacity: placeOrder.isPending ? 0.6 : 1 }}>
                {placeOrder.isPending ? "…" : "▼ SELL"}
              </button>
            </div>
          </div>

          {/* Open Positions — REAL */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>
              Open Positions ({positions.length})
            </div>
            {positions.length === 0 ? (
              <div style={{ color: "var(--text3)", fontSize: 12, textAlign: "center", padding: 12 }}>No open positions</div>
            ) : positions.map((p: any) => (
              <div key={p.symbol} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12, flex: 1 }}>{p.symbol}</span>
                <span style={{ fontSize: 11, color: "var(--text3)" }}>{p.quantity}@{p.avg_price?.toFixed(2)}</span>
                <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13, color: p.unrealized_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                  {p.unrealized_pnl >= 0 ? "+" : ""}{p.pnl_pct?.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>

          {/* Recent Orders — REAL */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>
              Recent Orders
            </div>
            {recentOrders.length === 0 ? (
              <div style={{ color: "var(--text3)", fontSize: 12, textAlign: "center", padding: 12 }}>No orders yet</div>
            ) : recentOrders.slice(0, 6).map((o: any) => (
              <div key={o.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ padding: "1px 7px", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 10,
                  background: o.side === "buy" ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)",
                  color: o.side === "buy" ? "var(--green)" : "var(--red)" }}>
                  {o.side?.toUpperCase()}
                </span>
                <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 12, flex: 1 }}>{o.symbol}</span>
                <span style={{ fontSize: 11, color: "var(--text3)" }}>{o.filled_quantity ?? o.quantity}</span>
                <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>
                  @{(o.avg_fill_price ?? o.price ?? 0).toFixed(2)}
                </span>
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}
