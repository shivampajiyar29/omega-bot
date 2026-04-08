"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { 
  useDashboardSummary, 
  useBots, 
  usePositions, 
  useOrders, 
  useMarketOverview 
} from "@/hooks/useApi";
import { Loader2, AlertCircle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

// ─── Sparkline component ──────────────────────────────────────────────────────
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

// ─── Equity canvas ────────────────────────────────────────────────────────────
function EquityCanvas({ points }: { points?: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const defaultPts = [100,103,99,105,108,104,110,107,115,112,118,116,122,119,125,123,129,127,132,138,134,140,138,143,141,148];
  const pts = points && points.length > 1 ? points : defaultPts;

  useEffect(() => {
    const c = ref.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const W = c.offsetWidth, H = 120;
    c.width = W; c.height = H;
    const mn = Math.min(...pts), mx = Math.max(...pts), rng = mx - mn || 1;
    const xs = pts.map((_, i) => i / (pts.length - 1) * W);
    const ys = pts.map(v => H - (v - mn) / rng * (H - 20) - 10);
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "rgba(0,212,160,0.2)");
    g.addColorStop(1, "rgba(0,212,160,0)");
    ctx.beginPath(); ctx.moveTo(xs[0], ys[0]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(xs[i], ys[i]);
    ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
    ctx.fillStyle = g; ctx.fill();
    ctx.beginPath(); ctx.moveTo(xs[0], ys[0]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(xs[i], ys[i]);
    ctx.strokeStyle = "var(--green)"; ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(xs[xs.length-1], ys[ys.length-1], 4, 0, Math.PI*2);
    ctx.fillStyle = "var(--green)"; ctx.fill();
  }, [pts]);

  return <canvas ref={ref} style={{ width: "100%", height: 120, display: "block" }} />;
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("all");
  const { data: summary, isLoading: subLoading, error: subError } = useDashboardSummary();
  const { data: bots, isLoading: botsLoading } = useBots();
  const { data: positions, isLoading: posLoading } = usePositions();
  const { data: recentOrders, isLoading: ordersLoading } = useOrders({ limit: 10 });
  const { data: marketData, isLoading: marketLoading } = useMarketOverview(marketScope);
  const qc = useQueryClient();
  const [syncTimedOut, setSyncTimedOut] = useState(false);

  const [eqTab, setEqTab] = useState<"1D" | "1W" | "1M">("1D");

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
    } else {
      setMarketScope("crypto");
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("omegabot_market_scope", marketScope);
  }, [marketScope]);

  const isSyncLoading = subLoading || botsLoading || posLoading || marketLoading || ordersLoading;
  useEffect(() => {
    if (!isSyncLoading) {
      setSyncTimedOut(false);
      return;
    }
    setSyncTimedOut(false);
    const t = setTimeout(() => setSyncTimedOut(true), 9000);
    return () => clearTimeout(t);
  }, [isSyncLoading]);

  const retrySync = () => {
    setSyncTimedOut(false);
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["bots"] });
    qc.invalidateQueries({ queryKey: ["positions"] });
    qc.invalidateQueries({ queryKey: ["orders"] });
    qc.invalidateQueries({ queryKey: ["market", "overview"] });
  };

  const totalPnl = summary?.total_pnl_today ?? 0;
  const portfolioValue = summary?.portfolio_value ?? 0;
  const activeBotsCount = summary?.active_bots ?? 0;
  const totalBotsCount = bots?.length ?? 0;

  if (isSyncLoading && !syncTimedOut) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: 12 }}>
        <Loader2 className="animate-spin" size={32} color="var(--blue)" />
        <span style={{ fontSize: 13, color: "var(--text3)", fontFamily: "Syne, sans-serif" }}>Synchronizing portfolio data...</span>
      </div>
    );
  }

  if (isSyncLoading && syncTimedOut) {
    return (
      <div style={{ background: "rgba(255,179,71,0.06)", border: "1px solid rgba(255,179,71,0.25)", borderRadius: 10, padding: 28, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
        <AlertCircle size={28} color="var(--amber)" />
        <div style={{ textAlign: "center" }}>
          <h3 style={{ fontFamily: "Syne, sans-serif", fontSize: 16, marginBottom: 4 }}>Portfolio sync is taking too long</h3>
          <p style={{ color: "var(--text3)", fontSize: 12 }}>The backend may be down or slow to respond.</p>
        </div>
        <button onClick={retrySync} style={{ padding: "8px 14px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 650 }}>
          Retry
        </button>
      </div>
    );
  }

  if (subError) {
    return (
      <div style={{ background: "rgba(255,71,87,0.05)", border: "1px solid rgba(255,71,87,0.2)", borderRadius: 10, padding: 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <AlertCircle size={32} color="var(--red)" />
        <div style={{ textAlign: "center" }}>
          <h3 style={{ fontFamily: "Syne, sans-serif", fontSize: 16, marginBottom: 4 }}>API Connection Error</h3>
          <p style={{ color: "var(--text3)", fontSize: 12 }}>Unable to reach the OmegaBot backend. Please check your connection.</p>
        </div>
        <button onClick={retrySync} style={{ padding: "8px 14px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 650 }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* ── Market overview ticker ─────────────────────────────────────── */}
      <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
        <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: 10 }}>
          Market Overview
        </div>
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          {(["crypto", "indian", "american", "all"] as const).map((scope) => (
            <button
              key={scope}
              onClick={() => setMarketScope(scope)}
              style={{
                padding: "3px 10px",
                borderRadius: 5,
                border: "1px solid var(--border)",
                background: marketScope === scope ? "var(--bg1)" : "var(--bg3)",
                color: marketScope === scope ? "var(--text)" : "var(--text3)",
                fontSize: 10,
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {scope}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 2 }}>
          {Array.isArray(marketData) && marketData.map((t: any) => (
            <div key={t.sym} style={{ flexShrink: 0, background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 14px", display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12 }}>{t.sym}</span>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>{t.price?.toLocaleString("en-IN")}</span>
              <span style={{ fontSize: 11, color: (t.pct ?? 0) >= 0 ? "var(--green)" : "var(--red)" }}>
                {(t.pct ?? 0) >= 0 ? "+" : ""}{(t.pct ?? 0).toFixed(2)}%
              </span>
            </div>
          ))}
          {(!marketData || marketData.length === 0) && (
            <div style={{ fontSize: 11, color: "var(--text3)", padding: "8px" }}>No live market data available</div>
          )}
        </div>
      </div>

      {/* ── Stat cards ─────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          { label: "Total P&L (Today)", value: `${totalPnl >= 0 ? "+" : ""}₹${totalPnl.toLocaleString("en-IN")}`, sub: "Today's performance", color: totalPnl >= 0 ? "var(--green)" : "var(--red)", spark: [100,102,101,104,106,105,108,107,110,112] },
          { label: "Portfolio Value",   value: `₹${portfolioValue.toLocaleString("en-IN")}`, sub: summary?.trading_mode?.toUpperCase() + " account", color: "var(--text)",  spark: [300,305,302,308,312,310,315,318,322,325] },
          { label: "Active Bots",       value: `${activeBotsCount} / ${totalBotsCount}`, sub: "Live instances", color: "var(--blue)",  spark: [3,3,4,4,3,3,3,4,3,3] },
          { label: "Alerts",            value: summary?.unread_alerts ?? 0, sub: "Unread notifications", color: "var(--purple)", spark: [0,1,0,2,1,0,3,1,0,0] },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>{s.label}</div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 4 }}>{s.sub}</div>
            <div style={{ marginTop: 8 }}><Sparkline points={s.spark} color={s.color === "var(--text)" ? "#8b90a0" : s.color} /></div>
          </div>
        ))}
      </div>

      {/* ── Middle row ─────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr", gap: 12 }}>

        {/* Equity curve */}
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Equity Curve</div>
            <div style={{ display: "flex", gap: 2 }}>
              {(["1D","1W","1M"] as const).map(t => (
                <button key={t} onClick={() => setEqTab(t)} style={{
                  padding: "3px 10px", borderRadius: 4, border: "1px solid transparent",
                  cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
                  background: eqTab === t ? "var(--bg1)" : "transparent",
                  color: eqTab === t ? "var(--text)" : "var(--text3)",
                  borderColor: eqTab === t ? "var(--border)" : "transparent",
                }}>{t}</button>
              ))}
            </div>
          </div>
          <EquityCanvas />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11 }}>
            <span style={{ color: "var(--text3)" }}>Baseline</span>
            <span style={{ color: "var(--green)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>Real-time projection</span>
            <span style={{ color: "var(--text3)" }}>₹{portfolioValue.toLocaleString("en-IN")}</span>
          </div>
        </div>

        {/* Active bots */}
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Active Bots</div>
            <a href="/strategy" style={{ fontSize: 10, color: "var(--blue)", textDecoration: "none" }}>+ New</a>
          </div>
          {bots && bots.length > 0 ? (
            bots.map((b: any) => (
              <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", background: "var(--bg3)", borderRadius: 6, marginBottom: 6, cursor: "pointer" }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                  background: b.status === "running" ? "var(--green)" : b.status === "paused" ? "var(--amber)" : "var(--text3)",
                  boxShadow: b.status === "running" ? "0 0 6px var(--green)" : "none",
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.name}</div>
                  <div style={{ fontSize: 10, color: "var(--text3)" }}>{b.symbol} · {b.status}</div>
                </div>
                <div style={{ width: 30, height: 17, borderRadius: 9, background: b.status === "running" ? "rgba(0,212,160,0.25)" : "var(--bg2)", position: "relative" }}>
                   <span style={{ position: "absolute", top: 2, left: b.status === "running" ? 14 : 2, width: 11, height: 11, borderRadius: "50%", background: b.status === "running" ? "var(--green)" : "var(--text3)" }} />
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: "var(--text3)", fontSize: 11, textAlign: "center", padding: "20px" }}>No active bots</div>
          )}
        </div>

        {/* Watchlist (Placeholder for now, same as market overview) */}
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Watchlist</div>
            <a href="/watchlist" style={{ fontSize: 10, color: "var(--blue)", textDecoration: "none" }}>+ Add</a>
          </div>
          {Array.isArray(marketData) && marketData.slice(0, 5).map((w: any) => (
            <a key={w.sym} href="/charts" style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: "1px solid var(--border)", textDecoration: "none" }}>
              <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 12, width: 56, color: "var(--text)" }}>{w.sym}</span>
              <span style={{ fontSize: 10, color: "var(--text3)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Instrument</span>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--text)", minWidth: 68, textAlign: "right" }}>
                ₹{w.price?.toLocaleString("en-IN")}
              </span>
              <span style={{
                fontSize: 10, minWidth: 50, textAlign: "right", padding: "2px 6px", borderRadius: 4,
                background: (w.chg ?? 0) >= 0 ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)",
                color: (w.chg ?? 0) >= 0 ? "var(--green)" : "var(--red)",
              }}>
                {(w.chg ?? 0) >= 0 ? "+" : ""}{(w.chg ?? 0).toFixed(2)}%
              </span>
            </a>
          ))}
        </div>
      </div>

      {/* ── Bottom row ─────────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr", gap: 12 }}>

        {/* Positions */}
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Open Positions</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 10, padding: "2px 8px", background: "rgba(0,212,160,0.1)", color: "var(--green)", border: "1px solid rgba(0,212,160,0.2)", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 500 }}>
                {positions?.length ?? 0} open
              </span>
              <a href="/positions" style={{ fontSize: 10, color: "var(--blue)", textDecoration: "none" }}>View all →</a>
            </div>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Symbol","Side","Qty","Avg","LTP","P&L"].map(h => (
                  <th key={h} style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", fontWeight: 500, textTransform: "uppercase", letterSpacing: "1px", padding: "4px 8px", textAlign: "left", borderBottom: "1px solid var(--border)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions && positions.length > 0 ? (
                positions.map((p: any) => (
                  <tr key={p.id} style={{ cursor: "pointer" }}>
                    <td style={{ padding: "9px 8px", fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 12 }}>{p.symbol}</td>
                    <td style={{ padding: "9px 8px" }}>
                      <span style={{ fontSize: 10, fontFamily: "Syne, sans-serif", fontWeight: 600, padding: "2px 7px", borderRadius: 4, background: p.side === "buy" ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)", color: p.side === "buy" ? "var(--green)" : "var(--red)" }}>
                        {p.side.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "9px 8px", fontSize: 12, color: "var(--text2)" }}>{p.quantity}</td>
                    <td style={{ padding: "9px 8px", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--text3)" }}>₹{p.avg_price?.toLocaleString("en-IN")}</td>
                    <td style={{ padding: "9px 8px", fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>₹{p.current_price?.toLocaleString("en-IN")}</td>
                    <td style={{ padding: "9px 8px", fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 12, color: (p.unrealized_pnl ?? 0) >= 0 ? "var(--green)" : "var(--red)" }}>
                      {(p.unrealized_pnl ?? 0) >= 0 ? "+" : ""}₹{(p.unrealized_pnl ?? 0).toLocaleString("en-IN")}
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: "20px", fontSize: 11, color: "var(--text3)" }}>No open positions</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Risk + Logs (Logs replaced with Recent Orders for now) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

          {/* Risk meters (Static for now, but configured with summary) */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Risk Center</div>
              <a href="/risk" style={{ fontSize: 10, color: "var(--blue)", textDecoration: "none" }}>Configure →</a>
            </div>
            {[
              { label: "Daily Loss", val: Math.min(100, (Math.abs(summary?.total_pnl_today ?? 0) / 10000) * 100), color: "var(--green)" },
              { label: "Margin Used", val: 42, color: "var(--amber)" },
              { label: "Positions",  val: Math.min(100, ((summary?.open_positions ?? 0) / 10) * 100), color: "var(--blue)" },
            ].map(r => (
              <div key={r.label} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                  <span style={{ color: "var(--text2)" }}>{r.label}</span>
                  <span style={{ color: "var(--text3)", fontSize: 10 }}>{r.val.toFixed(0)}%</span>
                </div>
                <div style={{ height: 5, background: "var(--bg3)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${r.val}%`, background: r.color, borderRadius: 3, transition: "width 1s ease" }} />
                </div>
              </div>
            ))}
          </div>

          {/* Recent Orders (Replacing mock logs) */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: "14px 16px", flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px" }}>Recent Orders</div>
              <a href="/orders" style={{ fontSize: 10, color: "var(--blue)", textDecoration: "none" }}>View all →</a>
            </div>
            {recentOrders && recentOrders.length > 0 ? (
              recentOrders.slice(0, 4).map((o: any) => (
                <div key={o.id} style={{
                  padding: "7px 10px", marginBottom: 5, borderRadius: "0 4px 4px 0",
                  background: "var(--bg3)", fontSize: 11, color: "var(--text2)",
                  borderLeft: `2px solid ${o.side === "buy" ? "var(--green)" : "var(--red)"}`,
                }}>
                  <span style={{ color: "var(--text3)", fontSize: 10, marginRight: 8 }}>{o.status.toUpperCase()}</span>
                  {o.side.toUpperCase()} {o.quantity} {o.symbol} @ {o.price ?? "MKT"}
                </div>
              ))
            ) : (
              <div style={{ color: "var(--text3)", fontSize: 11, textAlign: "center", padding: "20px" }}>No recent orders</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
