"use client";
import { useState, useEffect } from "react";
import { useStore } from "@/store/useStore";
import { toast } from "sonner";

const LIVE_FILLS = [
  { time: "14:32:11", sym: "RELIANCE", side: "BUY",  qty: 50,  price: 2831.00 },
  { time: "14:28:45", sym: "TCS",      side: "SELL", qty: 25,  price: 3924.00 },
  { time: "14:22:03", sym: "NIFTY FUT",side: "BUY",  qty: 1,   price: 24780.00 },
];

type Bot = { id: string; name: string; sym: string; status: "running"|"paused"|"stopped"; pnl: number; trades: number; signals: number };

const INIT_BOTS: Bot[] = [
  { id: "1", name: "EMA Crossover", sym: "RELIANCE",  status: "running", pnl: 2840,  trades: 12, signals: 18 },
  { id: "2", name: "RSI Breakout",  sym: "NIFTY FUT", status: "running", pnl: 1120,  trades: 7,  signals: 11 },
  { id: "3", name: "Mean Revert",   sym: "TCS",       status: "paused",  pnl: -380,  trades: 5,  signals: 9  },
];

export default function TradingPage() {
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");
  const [quickSymbol, setQuickSymbol] = useState("BTCUSDT");
  const { tradingMode } = useStore();
  const [bots, setBots] = useState<Bot[]>(INIT_BOTS);
  const [fills, setFills] = useState(LIVE_FILLS);
  const [totalPnl, setTotalPnl] = useState(3580);

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
    }
  }, []);

  useEffect(() => {
    if (marketScope === "indian") setQuickSymbol("RELIANCE");
    else if (marketScope === "american") setQuickSymbol("AAPL");
    else setQuickSymbol("BTCUSDT");
  }, [marketScope]);

  // Simulate live PnL updates
  useEffect(() => {
    const id = setInterval(() => {
      setBots(bs => bs.map(b => b.status === "running" ? {
        ...b,
        pnl: +(b.pnl + (Math.random() - 0.48) * 120).toFixed(0),
      } : b));
      setTotalPnl(p => +(p + (Math.random() - 0.48) * 80).toFixed(0));
    }, 2500);
    return () => clearInterval(id);
  }, []);

  const toggleBot = (id: string) => {
    setBots(bs => bs.map(b => {
      if (b.id !== id) return b;
      const next = b.status === "running" ? "paused" : "running";
      toast[next === "running" ? "success" : "info"](`${b.name} ${next}`);
      return { ...b, status: next };
    }));
  };

  const stopBot = (id: string) => {
    setBots(bs => bs.map(b => b.id !== id ? b : { ...b, status: "stopped" }));
    toast.warning("Bot stopped");
  };

  const isLive = tradingMode === "live";

  return (
    <div style={{ maxWidth: 1050 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>
            {isLive ? "Live Trading" : "Paper Trading"}
          </h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
            {isLive ? "Real orders — be careful." : "Simulated trading, no real money at risk."}
          </p>
        </div>

        {/* Mode indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 8, background: isLive ? "rgba(255,71,87,0.1)" : "rgba(255,179,71,0.1)", border: `1px solid ${isLive ? "rgba(255,71,87,0.3)" : "rgba(255,179,71,0.3)"}` }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: isLive ? "var(--red)" : "var(--amber)", boxShadow: `0 0 8px ${isLive ? "var(--red)" : "var(--amber)"}`, display: "inline-block" }} className="animate-pulse-dot" />
          <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12, color: isLive ? "var(--red)" : "var(--amber)", letterSpacing: "1px" }}>
            {isLive ? "LIVE" : "PAPER"}
          </span>
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { label: "Session P&L",    value: `${totalPnl >= 0 ? "+" : ""}₹${totalPnl.toLocaleString("en-IN")}`, color: totalPnl >= 0 ? "var(--green)" : "var(--red)" },
          { label: "Running Bots",   value: bots.filter(b => b.status === "running").length.toString(), color: "var(--blue)" },
          { label: "Fills Today",    value: fills.length.toString(), color: "var(--text)" },
          { label: "Open Positions", value: "3", color: "var(--text)" },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>{s.label}</div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>

        {/* Bot monitor panel */}
        <div>
          <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: 10 }}>Bot Monitor</div>
          {bots.map(b => (
            <div key={b.id} style={{ background: "var(--bg2)", border: `1px solid ${b.status === "running" ? "rgba(0,212,160,0.2)" : "var(--border)"}`, borderRadius: 10, padding: "14px 16px", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                {/* Status indicator */}
                <span style={{
                  width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
                  background: b.status === "running" ? "var(--green)" : b.status === "paused" ? "var(--amber)" : "var(--text3)",
                  boxShadow: b.status === "running" ? "0 0 8px var(--green)" : "none",
                }} className={b.status === "running" ? "animate-pulse-dot" : ""} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 13 }}>{b.name}</div>
                  <div style={{ fontSize: 10, color: "var(--text3)" }}>{b.sym} · {b.status.toUpperCase()}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 16, color: b.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    {b.pnl >= 0 ? "+" : ""}₹{b.pnl.toLocaleString("en-IN")}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text3)" }}>{b.trades} trades · {b.signals} signals</div>
                </div>
              </div>

              {/* Progress bar */}
              <div style={{ height: 4, background: "var(--bg3)", borderRadius: 2, marginBottom: 12, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${Math.min(Math.abs(b.pnl) / 50, 100)}%`, background: b.pnl >= 0 ? "var(--green)" : "var(--red)", borderRadius: 2, transition: "width 0.5s ease" }} />
              </div>

              {/* Controls */}
              <div style={{ display: "flex", gap: 7 }}>
                <button
                  onClick={() => toggleBot(b.id)}
                  disabled={b.status === "stopped"}
                  style={{
                    padding: "5px 14px", borderRadius: 5, cursor: b.status === "stopped" ? "not-allowed" : "pointer",
                    fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, border: "1px solid",
                    opacity: b.status === "stopped" ? 0.4 : 1,
                    background: b.status === "running" ? "rgba(255,179,71,0.1)" : "rgba(0,212,160,0.1)",
                    color: b.status === "running" ? "var(--amber)" : "var(--green)",
                    borderColor: b.status === "running" ? "rgba(255,179,71,0.3)" : "rgba(0,212,160,0.3)",
                  }}
                >
                  {b.status === "running" ? "⏸ Pause" : "▶ Start"}
                </button>
                <button
                  onClick={() => stopBot(b.id)}
                  disabled={b.status === "stopped"}
                  style={{ padding: "5px 14px", borderRadius: 5, cursor: b.status === "stopped" ? "not-allowed" : "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, opacity: b.status === "stopped" ? 0.4 : 1, background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.2)", color: "var(--red)" }}
                >
                  ⊘ Stop
                </button>
                <button style={{ padding: "5px 12px", borderRadius: 5, cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text2)" }}>
                  Config
                </button>
              </div>
            </div>
          ))}

          {/* Add bot button */}
          <a href="/strategy" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "11px", background: "transparent", border: "1px dashed var(--border2)", borderRadius: 10, color: "var(--text3)", fontSize: 12, fontFamily: "Syne, sans-serif", textDecoration: "none", cursor: "pointer" }}>
            + Deploy new bot
          </a>
        </div>

        {/* Right column: fills + order book */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Recent fills */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>Recent Fills</div>
            {fills.map((f, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", borderBottom: i < fills.length - 1 ? "1px solid var(--border)" : "none" }}>
                <span style={{ fontSize: 10, color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace", minWidth: 54 }}>{f.time}</span>
                <span style={{ fontSize: 10, padding: "1px 7px", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 600, background: f.side === "BUY" ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)", color: f.side === "BUY" ? "var(--green)" : "var(--red)" }}>
                  {f.side}
                </span>
                <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 12, flex: 1 }}>{f.sym}</span>
                <span style={{ fontSize: 11, color: "var(--text2)" }}>{f.qty} @ </span>
                <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>₹{f.price.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>

          {/* Quick order panel */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 12 }}>Quick Order</div>
            {[
              { label: "Symbol", type: "text",   placeholder: marketScope === "crypto" ? "BTCUSDT" : marketScope === "american" ? "AAPL" : "RELIANCE" },
              { label: "Qty",    type: "number", placeholder: "50" },
              { label: "Price",  type: "number", placeholder: "Market" },
            ].map(f => (
              <div key={f.label} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4 }}>{f.label}</div>
                {f.label === "Symbol" ? (
                  <input value={quickSymbol} onChange={(e) => setQuickSymbol(e.target.value.toUpperCase())} type={f.type} placeholder={f.placeholder} style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none" }} />
                ) : (
                  <input type={f.type} placeholder={f.placeholder} style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none" }} />
                )}
              </div>
            ))}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 4 }}>
              <button onClick={() => toast.success("BUY order placed (paper)")} style={{ padding: "9px", background: "rgba(0,212,160,0.12)", border: "1px solid rgba(0,212,160,0.3)", borderRadius: 6, color: "var(--green)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                ▲ BUY
              </button>
              <button onClick={() => toast.success("SELL order placed (paper)")} style={{ padding: "9px", background: "rgba(255,71,87,0.12)", border: "1px solid rgba(255,71,87,0.3)", borderRadius: 6, color: "var(--red)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                ▼ SELL
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
