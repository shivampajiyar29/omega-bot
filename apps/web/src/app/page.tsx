"use client";
import { useState, useEffect, useRef } from "react";
import {
  useDashboardSummary, useBots, usePositions,
  useOrders, useMarketOverview, useAISignals,
} from "@/hooks/useApi";
import { useMarketFeed } from "@/hooks/useMarketFeed";
import { useQueryClient } from "@tanstack/react-query";

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ points, color }: { points: number[]; color: string }) {
  if (!points || points.length < 2) return <div style={{ height: 36 }} />;
  const W = 120, H = 36;
  const mn = Math.min(...points), mx = Math.max(...points), rng = mx - mn || 1;
  const xs = points.map((_, i) => (i / (points.length - 1)) * W);
  const ys = points.map(v => H - ((v - mn) / rng) * (H - 6) - 3);
  const d = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  const fill = `${d} L${W},${H} L0,${H} Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 36 }}>
      <path d={fill} fill={color} fillOpacity={0.12} />
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}

// ── Equity Canvas ─────────────────────────────────────────────────────────────
function EquityCanvas({ points }: { points?: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const pts = points && points.length > 1 ? points : [100,103,99,105,108,104,110,107,115,112,118];
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const W = c.offsetWidth || 400, H = 100;
    c.width = W; c.height = H;
    const mn = Math.min(...pts), mx = Math.max(...pts), rng = mx - mn || 1;
    const xs = pts.map((_, i) => i / (pts.length - 1) * W);
    const ys = pts.map(v => H - (v - mn) / rng * (H - 20) - 10);
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "rgba(0,212,160,0.2)"); g.addColorStop(1, "rgba(0,212,160,0)");
    ctx.beginPath(); ctx.moveTo(xs[0], ys[0]);
    xs.forEach((x, i) => ctx.lineTo(x, ys[i]));
    ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
    ctx.fillStyle = g; ctx.fill();
    ctx.beginPath(); ctx.moveTo(xs[0], ys[0]);
    xs.forEach((x, i) => ctx.lineTo(x, ys[i]));
    ctx.strokeStyle = "#00d4a0"; ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(xs[xs.length-1], ys[ys.length-1], 4, 0, Math.PI*2);
    ctx.fillStyle = "#00d4a0"; ctx.fill();
  }, [pts]);
  return <canvas ref={ref} style={{ width: "100%", height: 100, display: "block" }} />;
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [marketScope, setMarketScope] = useState<"all"|"crypto"|"indian">("crypto");

  const { data: summary }      = useDashboardSummary();
  const { data: bots = [] }    = useBots();
  const { data: positions = [] } = usePositions(true);
  const { data: orders = [] }  = useOrders({ limit: 8 });
  const { data: market = [] }  = useMarketOverview(marketScope);
  const { data: aiSignals = [] } = useAISignals();

  // Live price feed
  const allSyms = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","RELIANCE","TCS","INFY"];
  const { prices, connected } = useMarketFeed({ symbols: allSyms });

  const qc = useQueryClient();
  useEffect(() => {
    const id = setInterval(() => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
    }, 5000);
    return () => clearInterval(id);
  }, [qc]);

  const runningBots   = bots.filter((b: any) => b.status === "running").length;
  const openPositions = Array.isArray(positions) ? positions.length : 0;
  const unrealizedPnl = Array.isArray(positions)
    ? positions.reduce((s: number, p: any) => s + (p.unrealized_pnl ?? 0), 0)
    : (summary as any)?.unrealized_pnl ?? 0;
  const portfolioVal  = (summary as any)?.portfolio_value ?? 1_000_000;
  const ordersToday   = (summary as any)?.orders_today ?? orders.length;

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
        <div>
          <h1 style={{ fontFamily:"Syne,sans-serif", fontSize:22, fontWeight:800 }}>Dashboard</h1>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:4 }}>
            <span style={{ width:7, height:7, borderRadius:"50%", background: connected ? "var(--green)" : "var(--amber)", display:"inline-block" }}/>
            <span style={{ fontSize:11, color:"var(--text3)" }}>
              {connected ? "Live WebSocket" : "Connecting…"} ·{" "}
              {aiSignals.length} AI signals active
            </span>
          </div>
        </div>
        <div style={{ display:"flex", gap:6 }}>
          {(["crypto","indian","all"] as const).map(s => (
            <button key={s} onClick={() => setMarketScope(s)}
              style={{ padding:"5px 12px", borderRadius:5, border:"none", cursor:"pointer",
                fontFamily:"Syne,sans-serif", fontSize:11, fontWeight:500,
                background: marketScope === s ? "var(--bg1)" : "var(--bg3)",
                color: marketScope === s ? "var(--text)" : "var(--text3)" }}>
              {s.charAt(0).toUpperCase()+s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10, marginBottom:16 }}>
        {[
          { label:"Portfolio Value",  value:`₹${portfolioVal.toLocaleString("en-IN",{maximumFractionDigits:0})}`, color:"var(--text)",  sub:"Paper capital" },
          { label:"Unrealized P&L",   value:`${unrealizedPnl>=0?"+":""}₹${unrealizedPnl.toLocaleString("en-IN",{maximumFractionDigits:2})}`, color: unrealizedPnl>=0?"var(--green)":"var(--red)", sub:"Open positions" },
          { label:"Running Bots",     value: runningBots.toString(),  color:"var(--blue)",  sub:`${bots.length} total` },
          { label:"Open Positions",   value: openPositions.toString(), color:"var(--text)", sub:`${ordersToday} orders today` },
        ].map((c: any) => (
          <div key={c.label} style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px", marginBottom:6 }}>{c.label}</div>
            <div style={{ fontFamily:"Syne,sans-serif", fontSize:22, fontWeight:700, color:c.color }}>{c.value}</div>
            <div style={{ fontSize:10, color:"var(--text3)", marginTop:4 }}>{c.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1.6fr 1fr", gap:14 }}>

        {/* LEFT column */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>

          {/* Market Overview */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px", marginBottom:12 }}>
              Market Overview
            </div>
            {market.length === 0 ? (
              <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:16 }}>Loading prices…</div>
            ) : (
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
                {market.slice(0,6).map((m: any) => {
                  const livePx = prices[m.symbol];
                  const px     = livePx ?? m.price ?? 0;
                  const pct    = m.change_pct ?? m.pct ?? 0;
                  return (
                    <div key={m.symbol} style={{ background:"var(--bg3)", borderRadius:8, padding:"10px 12px" }}>
                      <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif", marginBottom:4 }}>{m.symbol}</div>
                      <div style={{ fontFamily:"IBM Plex Mono,monospace", fontWeight:700, fontSize:14 }}>
                        {px > 100 ? px.toLocaleString("en-IN",{maximumFractionDigits:2}) : px.toFixed(4)}
                      </div>
                      <div style={{ fontSize:11, marginTop:2, color: pct>=0?"var(--green)":"var(--red)" }}>
                        {pct>=0?"+":""}{pct.toFixed(2)}%
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Open Positions */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
              <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px" }}>
                Open Positions ({openPositions})
              </div>
              <a href="/positions" style={{ fontSize:11, color:"var(--blue)", textDecoration:"none" }}>View all →</a>
            </div>
            {openPositions === 0 ? (
              <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"16px 0" }}>
                No open positions · <a href="/trading" style={{ color:"var(--blue)" }}>Start trading →</a>
              </div>
            ) : (
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr>
                    {["Symbol","Side","Qty","Avg Price","Live Price","P&L"].map(h => (
                      <th key={h} style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif", textAlign:"left", padding:"4px 8px", borderBottom:"1px solid var(--border)", fontWeight:500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(Array.isArray(positions) ? positions : []).slice(0,6).map((p: any) => {
                    const livePx = prices[p.symbol] ?? p.current_price ?? p.avg_price;
                    const unr    = (livePx - p.avg_price) * p.quantity;
                    return (
                      <tr key={p.id}>
                        <td style={{ padding:"8px", fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:13 }}>{p.symbol}</td>
                        <td style={{ padding:"8px" }}>
                          <span style={{ padding:"2px 8px", borderRadius:4, fontFamily:"Syne,sans-serif", fontSize:10, fontWeight:600,
                            background: p.side==="buy"?"rgba(0,212,160,0.1)":"rgba(255,71,87,0.1)",
                            color: p.side==="buy"?"var(--green)":"var(--red)" }}>
                            {p.side?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding:"8px", fontFamily:"IBM Plex Mono,monospace", fontSize:12 }}>{p.quantity}</td>
                        <td style={{ padding:"8px", fontFamily:"IBM Plex Mono,monospace", fontSize:12 }}>{Number(p.avg_price).toFixed(2)}</td>
                        <td style={{ padding:"8px", fontFamily:"IBM Plex Mono,monospace", fontSize:12, color:"var(--green)" }}>{Number(livePx).toFixed(2)}</td>
                        <td style={{ padding:"8px", fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:12, color: unr>=0?"var(--green)":"var(--red)" }}>
                          {unr>=0?"+":""}₹{unr.toFixed(2)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Recent Orders */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
              <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px" }}>
                Recent Orders
              </div>
              <a href="/orders" style={{ fontSize:11, color:"var(--blue)", textDecoration:"none" }}>View all →</a>
            </div>
            {orders.length === 0 ? (
              <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"16px 0" }}>No orders yet</div>
            ) : orders.slice(0,6).map((o: any) => (
              <div key={o.id} style={{ display:"flex", alignItems:"center", gap:10, padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ padding:"2px 8px", borderRadius:4, fontFamily:"Syne,sans-serif", fontWeight:600, fontSize:10,
                  background: o.side==="buy"?"rgba(0,212,160,0.1)":"rgba(255,71,87,0.1)",
                  color: o.side==="buy"?"var(--green)":"var(--red)" }}>
                  {o.side?.toUpperCase()}
                </span>
                <span style={{ fontFamily:"Syne,sans-serif", fontWeight:600, fontSize:12, flex:1 }}>{o.symbol}</span>
                <span style={{ fontSize:11, color:"var(--text3)" }}>{o.filled_quantity ?? o.quantity}</span>
                <span style={{ fontFamily:"IBM Plex Mono,monospace", fontSize:11 }}>
                  @{(o.avg_fill_price ?? o.price ?? 0).toFixed(2)}
                </span>
                <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4, background:"var(--bg3)",
                  color: o.status==="filled"?"var(--green)":"var(--text3)" }}>
                  {o.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT column */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>

          {/* Bot Status */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
              <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px" }}>
                Bots ({bots.length})
              </div>
              <a href="/trading" style={{ fontSize:11, color:"var(--blue)", textDecoration:"none" }}>Manage →</a>
            </div>
            {bots.length === 0 ? (
              <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"16px 0" }}>
                No bots · <a href="/strategy" style={{ color:"var(--blue)" }}>Create one →</a>
              </div>
            ) : bots.slice(0,5).map((b: any) => (
              <div key={b.id} style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ width:8, height:8, borderRadius:"50%", flexShrink:0,
                  background: b.status==="running"?"var(--green)":b.status==="paused"?"var(--amber)":"var(--text3)" }}/>
                <span style={{ fontFamily:"Syne,sans-serif", fontWeight:600, fontSize:12, flex:1 }}>{b.name}</span>
                <span style={{ fontSize:10, color:"var(--text3)" }}>{b.symbol}</span>
                <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4, background:"var(--bg3)", color:"var(--text3)" }}>
                  {b.status}
                </span>
              </div>
            ))}
          </div>

          {/* AI Signals */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
              <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px" }}>
                AI Signals
              </div>
              <a href="/screener" style={{ fontSize:11, color:"var(--blue)", textDecoration:"none" }}>Screener →</a>
            </div>
            {aiSignals.length === 0 ? (
              <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"16px 0" }}>
                No signals yet. Start a bot to generate signals.
              </div>
            ) : aiSignals.slice(0,6).map((sig: any) => (
              <div key={sig.symbol} style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 0", borderBottom:"1px solid var(--border)" }}>
                <span style={{ fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:12, width:72, flexShrink:0 }}>{sig.symbol}</span>
                <span style={{ padding:"2px 8px", borderRadius:4, fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:10,
                  background: sig.action==="buy"?"rgba(0,212,160,0.1)":sig.action==="sell"?"rgba(255,71,87,0.1)":"rgba(255,179,71,0.08)",
                  color: sig.action==="buy"?"var(--green)":sig.action==="sell"?"var(--red)":"var(--amber)" }}>
                  {sig.action?.toUpperCase()}
                </span>
                <span style={{ flex:1, fontSize:10, color:"var(--text3)" }}>{(sig.confidence*100).toFixed(0)}%</span>
                <span style={{ fontSize:9, color:"var(--text3)" }}>{sig.source}</span>
              </div>
            ))}
          </div>

          {/* Quick actions */}
          <div style={{ background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:10, padding:"14px 16px" }}>
            <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"Syne,sans-serif", textTransform:"uppercase", letterSpacing:"1px", marginBottom:12 }}>
              Quick Actions
            </div>
            {[
              { label:"▶ Paper Trade",   href:"/trading",   color:"var(--green)" },
              { label:"📊 Backtest",      href:"/backtest",  color:"var(--blue)" },
              { label:"🔍 Screener",      href:"/screener",  color:"var(--amber)" },
              { label:"⚡ New Strategy",  href:"/strategy",  color:"var(--text)" },
            ].map(a => (
              <a key={a.href} href={a.href}
                style={{ display:"flex", alignItems:"center", padding:"9px 12px", borderRadius:7, marginBottom:6,
                  background:"var(--bg3)", textDecoration:"none", color:a.color,
                  fontFamily:"Syne,sans-serif", fontWeight:600, fontSize:12, border:"1px solid var(--border)" }}>
                {a.label}
              </a>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}
