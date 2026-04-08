"use client";
import { useClosePosition, usePositions } from "@/hooks/useApi";

export default function PositionsPage() {
  const { data: positions = [], isLoading, error, refetch } = usePositions(true);
  const closePosition = useClosePosition();

  const totalPnl = (positions as any[]).reduce((s, p: any) => s + Number(p.unrealized_pnl ?? 0), 0);
  const totalValue = (positions as any[]).reduce((s, p: any) => s + Number((p.current_price ?? p.avg_price) * p.quantity), 0);

  return (
    <div style={{ maxWidth: 1000 }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Open Positions</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>Live position data from backend.</p>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && (
        <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div style={{ color: "var(--red)", fontSize: 12 }}>Failed to load positions (backend may be down)</div>
          <button
            onClick={() => refetch()}
            style={{ padding: "6px 10px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600 }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 16 }}>
        <MetricCard label="Total Positions" value={positions.length.toString()} />
        <MetricCard label="Positions Value" value={`₹${totalValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`} />
        <MetricCard label="Unrealized P&L" value={`${totalPnl >= 0 ? "+" : ""}₹${totalPnl.toFixed(0)}`} color={totalPnl >= 0 ? "var(--green)" : "var(--red)"} />
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Symbol</th><th>Side</th><th>Qty</th><th>Avg Price</th>
              <th>LTP</th><th>Change</th><th>P&L</th><th>P&L %</th>
              <th>Value</th><th>Mode</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(positions as any[]).map((p: any) => {
              const ltp = Number(p.current_price ?? p.avg_price);
              const avg = Number(p.avg_price ?? 0);
              const qty = Number(p.quantity ?? 0);
              const pnl = Number(p.unrealized_pnl ?? 0);
              const pnlPct = avg ? (pnl / (avg * qty)) * 100 : 0;
              return (
              <tr key={p.id}>
                <td>
                  <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600 }}>{p.symbol}</div>
                  <div style={{ fontSize: 10, color: "var(--text3)" }}>{p.exchange}</div>
                </td>
                <td>
                  <span style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    fontFamily: "Syne, sans-serif", fontWeight: 600,
                    background: p.side === "buy" ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)",
                    color: p.side === "buy" ? "var(--green)" : "var(--red)",
                  }}>
                    {p.side === "buy" ? "LONG" : "SHORT"}
                  </span>
                </td>
                <td>{qty}</td>
                <td style={{ fontFamily: "IBM Plex Mono, monospace" }}>₹{avg.toLocaleString("en-IN")}</td>
                <td style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 500 }}>
                  ₹{ltp.toLocaleString("en-IN")}
                </td>
                <td style={{ fontFamily: "IBM Plex Mono, monospace", color: pnlPct >= 0 ? "var(--green)" : "var(--red)", fontSize: 11 }}>
                  {pnlPct >= 0 ? "▲" : "▼"} {Math.abs(pnlPct).toFixed(2)}%
                </td>
                <td style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, color: pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                  {pnl >= 0 ? "+" : ""}₹{pnl.toFixed(0)}
                </td>
                <td style={{ color: pnlPct >= 0 ? "var(--green)" : "var(--red)", fontSize: 11 }}>
                  {pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%
                </td>
                <td style={{ fontFamily: "IBM Plex Mono, monospace", color: "var(--text2)", fontSize: 11 }}>
                  ₹{(ltp * qty).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </td>
                <td>
                  <span style={{ fontSize: 10, padding: "2px 7px", background: "var(--bg3)", borderRadius: 4, color: "var(--text3)" }}>
                    {String(p.trading_mode ?? "paper").toUpperCase()}
                  </span>
                </td>
                <td>
                  <button
                    onClick={() => closePosition.mutate(p.id)}
                    style={{ fontSize: 10, padding: "3px 10px", background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.2)", borderRadius: 4, color: "var(--red)", cursor: "pointer", fontFamily: "Syne, sans-serif" }}
                  >
                    Close
                  </button>
                </td>
              </tr>
            )})}
            {!isLoading && !error && (positions as any[]).length === 0 && (
              <tr>
                <td colSpan={11} style={{ padding: 26, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
                  No open positions yet. Run paper trading or execute a strategy to create positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="card">
      <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "Syne, sans-serif", fontSize: 22, fontWeight: 700, color: color ?? "var(--text)" }}>{value}</div>
    </div>
  );
}
