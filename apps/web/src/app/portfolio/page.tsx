"use client";
import { useState } from "react";
import { usePortfolioAllocation, usePortfolioEquityCurve, usePortfolioSummary, usePositions } from "@/hooks/useApi";

const PERIODS: Record<string, string> = { "1W": "1w", "1M": "1m", "3M": "3m", "1Y": "1y" };

export default function PortfolioPage() {
  const [period, setPeriod] = useState("1M");
  const { data: summary, isLoading, error } = usePortfolioSummary();
  const { data: allocation = [] } = usePortfolioAllocation();
  const { data: positions = [] } = usePositions();
  const { data: curveRaw = [] } = usePortfolioEquityCurve(PERIODS[period]);
  const curve: Array<{ date: string; value: number }> = curveRaw.map((c: any) => ({
    date: new Date(c.date).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
    value: c.value,
  }));
  const W = 800, H = 140;
  const vals = curve.map(c => c.value);
  const mn = vals.length ? Math.min(...vals) : 0;
  const mx = vals.length ? Math.max(...vals) : 1;
  const rng = mx - mn || 1;
  const xs = vals.map((_, i) => (i / (vals.length - 1)) * W);
  const ys = vals.map(v => H - ((v - mn) / rng) * (H - 16) - 8);
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");
  const fill = `${path} L${W} ${H} L0 ${H} Z`;
  const finalUp = vals.length ? vals[vals.length - 1] >= vals[0] : true;

  const totalPnl = summary?.total_pnl ?? 0;

  return (
    <div style={{ maxWidth: 1000 }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Portfolio</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>Paper trading account overview.</p>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && <div style={{ marginBottom: 12, color: "var(--red)", fontSize: 12 }}>Failed to load portfolio</div>}

      {/* Summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { label: "Portfolio Value", value: `₹${(summary?.total_value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, change: null },
          { label: "Unrealized P&L",  value: `+₹${totalPnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, change: "+2.4%", up: true },
          { label: "Available Cash",  value: `₹${(summary?.cash ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, change: null },
          { label: "Total Return",    value: `${(summary?.total_return_pct ?? 0) >= 0 ? "+" : ""}${(summary?.total_return_pct ?? 0).toFixed(2)}%`, change: "since start", up: (summary?.total_return_pct ?? 0) >= 0 },
        ].map((s) => (
          <div key={s.label} className="card">
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>{s.label}</div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700, color: s.up ? "var(--green)" : "var(--text)" }}>{s.value}</div>
            {s.change && <div style={{ fontSize: 11, color: s.up ? "var(--green)" : "var(--text3)", marginTop: 5 }}>{s.change}</div>}
          </div>
        ))}
      </div>

      {/* Equity curve */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600 }}>Equity Curve</div>
          <div style={{ display: "flex", gap: 3 }}>
            {Object.keys(PERIODS).map((p) => (
              <button key={p} onClick={() => setPeriod(p)} style={{
                padding: "3px 11px", borderRadius: 4, border: "1px solid var(--border)", cursor: "pointer",
                fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
                background: period === p ? "var(--bg3)" : "transparent",
                color: period === p ? "var(--text)" : "var(--text3)",
              }}>{p}</button>
            ))}
          </div>
        </div>
        {curve.length > 1 ? <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 140 }}>
          <defs>
            <linearGradient id="pf-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={finalUp ? "var(--green)" : "var(--red)"} stopOpacity="0.18" />
              <stop offset="100%" stopColor={finalUp ? "var(--green)" : "var(--red)"} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={fill} fill="url(#pf-fill)" />
          <path d={path} fill="none" stroke={finalUp ? "var(--green)" : "var(--red)"} strokeWidth="2" />
        </svg> : <div style={{ height: 140, display: "grid", placeItems: "center", color: "var(--text3)", fontSize: 12 }}>No equity curve data</div>}
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text3)", marginTop: 4 }}>
          <span>{curve[0]?.date}</span>
          <span style={{ color: finalUp ? "var(--green)" : "var(--red)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>
            ₹{vals[vals.length - 1]?.toLocaleString("en-IN")}
          </span>
          <span>{curve[curve.length - 1]?.date}</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 16 }}>

        {/* Allocation */}
        <div className="card">
          <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, marginBottom: 14 }}>Allocation</div>
          {allocation.map((a: any) => (
            <div key={a.name} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 5 }}>
                <span style={{ color: "var(--text)" }}>{a.name}</span>
                <span style={{ color: "var(--blue)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>{a.pct}%</span>
              </div>
              <div style={{ height: 5, background: "var(--bg3)", borderRadius: 3 }}>
                <div style={{ height: "100%", width: `${a.pct}%`, background: "var(--blue)", borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>

        {/* Holdings table */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, borderBottom: "1px solid var(--border)" }}>Holdings</div>
          <table className="data-table">
            <thead><tr><th>Symbol</th><th>Type</th><th>Qty</th><th>Avg</th><th>LTP</th><th>P&L</th></tr></thead>
            <tbody>
              {(positions as any[]).map((p: any) => (
                <tr key={p.id}>
                  <td style={{ fontFamily: "Syne, sans-serif", fontWeight: 600 }}>{p.symbol}</td>
                  <td><span style={{ fontSize: 10, padding: "1px 6px", background: "var(--bg3)", borderRadius: 3, color: "var(--text3)" }}>{String(p.market_type ?? "").toUpperCase()}</span></td>
                  <td>{p.quantity}</td>
                  <td style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>₹{Number(p.avg_price ?? 0).toLocaleString("en-IN")}</td>
                  <td style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11 }}>₹{Number((p.current_price ?? p.avg_price) ?? 0).toLocaleString("en-IN")}</td>
                  <td style={{ color: Number(p.unrealized_pnl ?? 0) >= 0 ? "var(--green)" : "var(--red)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>
                    {Number(p.unrealized_pnl ?? 0) >= 0 ? "+" : ""}₹{Number(p.unrealized_pnl ?? 0).toFixed(0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
