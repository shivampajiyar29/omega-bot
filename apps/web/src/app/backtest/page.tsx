"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useBacktests, useCreateBacktest, useStrategies } from "@/hooks/useApi";

const EMPTY_RESULTS = {
  total_return_pct: 0,
  sharpe_ratio: 0,
  max_drawdown_pct: 0,
  win_rate_pct: 0,
  total_trades: 0,
  profit_factor: 0,
  avg_win: 0,
  avg_loss: 0,
};

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function fmtMaybeNumber(v: unknown, fmt: (n: number) => string, empty = "N/A"): string {
  const n = typeof v === "string" ? Number(v) : (v as number);
  if (!Number.isFinite(n)) return empty;
  return fmt(n);
}

export default function BacktestPage() {
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");
  const { data: strategies = [] } = useStrategies();
  const { data: backtests = [], isLoading, error } = useBacktests();
  const createBacktest = useCreateBacktest();
  const [view, setView] = useState<"setup" | "results">("results");
  const [activeTab, setActiveTab] = useState<"equity" | "trades" | "monthly">("equity");

  // Setup form state
  const [setup, setSetup] = useState({
    strategy: "", symbol: "BTCUSDT", exchange: "BINANCE",
    timeframe: "15m", start: "2024-01-01", end: "2024-09-30",
    capital: "100000", commission: "0.03", slippage: "0.01",
  });

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
      if (saved === "indian") setSetup((s) => ({ ...s, symbol: "RELIANCE", exchange: "NSE" }));
      else if (saved === "american") setSetup((s) => ({ ...s, symbol: "AAPL", exchange: "NASDAQ" }));
      else setSetup((s) => ({ ...s, symbol: "BTCUSDT", exchange: "BINANCE" }));
    }
  }, []);

  const runBacktest = () => {
    toast.loading("Running backtest…", { id: "bt" });
    createBacktest.mutate({
      strategy_id: setup.strategy,
      symbol: setup.symbol,
      exchange: setup.exchange,
      timeframe: setup.timeframe,
      start_date: setup.start,
      end_date: setup.end,
      initial_capital: Number(setup.capital),
      commission_pct: Number(setup.commission),
      slippage_pct: Number(setup.slippage),
    }, {
      onSuccess: () => {
        toast.success("Backtest started", { id: "bt" });
        setView("results");
      },
      onError: () => toast.error("Backtest failed to start", { id: "bt" }),
    });
  };
  const latest: any = backtests[0] ?? null;
  const resultData: any = latest?.results ?? EMPTY_RESULTS;
  const equityData: any[] = latest?.equity_curve ?? [];
  const tradeData: any[] = latest?.trade_log ?? [];
  const hasResults =
    !!latest &&
    ((Array.isArray(equityData) && equityData.length > 1) ||
      (Array.isArray(tradeData) && tradeData.length > 0) ||
      Number(resultData?.total_trades ?? 0) > 0);

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Tabs */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Backtester</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>Test strategies on historical data before trading live.</p>
        </div>
        <div style={{ display: "flex", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, padding: 3, gap: 2 }}>
          {(["setup", "results"] as const).map((v) => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: "5px 16px", borderRadius: 4, border: "none", cursor: "pointer",
              fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
              background: view === v ? "var(--bg1)" : "transparent",
              color: view === v ? "var(--text)" : "var(--text3)",
            }}>
              {v === "setup" ? "⚙ Setup" : "📊 Results"}
            </button>
          ))}
        </div>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && <div style={{ marginBottom: 12, color: "var(--red)", fontSize: 12 }}>Failed to load backtests</div>}

      {view === "setup" ? (
        /* ── Setup Form ─────────────────────────────────────────────────── */
        <div className="card" style={{ maxWidth: 640 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, marginBottom: 16 }}>
            Configure Backtest
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Strategy">
              <select value={setup.strategy} onChange={e => setSetup(s=>({...s,strategy:e.target.value}))} style={inputSt}>
                <option value="">Select strategy</option>
                {(strategies as any[]).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </Field>
            <Field label="Symbol"><input value={setup.symbol} onChange={e => setSetup(s=>({...s,symbol:e.target.value}))} style={inputSt} /></Field>
            <Field label="Exchange">
              <select value={setup.exchange} onChange={e => setSetup(s=>({...s,exchange:e.target.value}))} style={inputSt}>
                {marketScope !== "crypto" && <option value="NSE">NSE</option>}
                {marketScope !== "crypto" && <option value="BSE">BSE</option>}
                {marketScope !== "indian" && <option value="BINANCE">Binance</option>}
                {marketScope !== "indian" && <option value="NASDAQ">NASDAQ</option>}
                {marketScope !== "indian" && <option value="NYSE">NYSE</option>}
              </select>
            </Field>
            <Field label="Timeframe"><select value={setup.timeframe} onChange={e => setSetup(s=>({...s,timeframe:e.target.value}))} style={inputSt}>{["1m","5m","15m","30m","1h","4h","1d"].map(t=><option key={t} value={t}>{t}</option>)}</select></Field>
            <Field label="Initial Capital (₹)"><input type="number" value={setup.capital} onChange={e => setSetup(s=>({...s,capital:e.target.value}))} style={inputSt} /></Field>
            <Field label="Start Date"><input type="date" value={setup.start} onChange={e => setSetup(s=>({...s,start:e.target.value}))} style={inputSt} /></Field>
            <Field label="End Date"><input type="date" value={setup.end} onChange={e => setSetup(s=>({...s,end:e.target.value}))} style={inputSt} /></Field>
            <Field label="Commission (%)"><input type="number" step="0.01" value={setup.commission} onChange={e => setSetup(s=>({...s,commission:e.target.value}))} style={inputSt} /></Field>
            <Field label="Slippage (%)"><input type="number" step="0.01" value={setup.slippage} onChange={e => setSetup(s=>({...s,slippage:e.target.value}))} style={inputSt} /></Field>
          </div>
          <button onClick={runBacktest} style={{ marginTop: 16, padding: "9px 24px", background: "var(--blue)", color: "#fff", border: "none", borderRadius: 7, fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, cursor: "pointer", width: "100%" }}>
            ▶ Run Backtest
          </button>
        </div>
      ) : (
        /* ── Results ──────────────────────────────────────────────────────── */
        <div>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <div style={{ fontFamily: "Syne, sans-serif", fontSize: 14, fontWeight: 600 }}>{latest?.name ?? "No backtest results yet"}</div>
              <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>
                {(latest?.start_date ?? "-")} → {(latest?.end_date ?? "-")} · {(latest?.timeframe ?? "-")} · ₹{Number(latest?.initial_capital ?? 0).toLocaleString()} initial
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => toast.info("Exporting CSV…")} style={ghostBtn}>Export CSV</button>
              <button onClick={() => toast.info("Exporting JSON…")} style={ghostBtn}>Export JSON</button>
              <button onClick={() => setView("setup")} style={ghostBtn}>← Edit Setup</button>
            </div>
          </div>

          {!hasResults ? (
            <div
              style={{
                background: "var(--bg2)",
                border: "1px dashed var(--border)",
                borderRadius: 10,
                padding: 28,
                color: "var(--text3)",
                fontSize: 12,
                textAlign: "center",
              }}
            >
              Run a backtest to see results.
            </div>
          ) : (
            <>
              {/* Summary metrics */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 14 }}>
                {[
                  {
                    label: "Total Return",
                    value: fmtMaybeNumber(resultData.total_return_pct, (n) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`),
                    pnl: true,
                  },
                  { label: "Sharpe Ratio", value: fmtMaybeNumber(resultData.sharpe_ratio, (n) => n.toFixed(2)) },
                  {
                    label: "Max Drawdown",
                    value: fmtMaybeNumber(resultData.max_drawdown_pct, (n) => `${n <= 0 ? "" : "-"}${Math.abs(n).toFixed(2)}%`),
                    neg: true,
                  },
                  { label: "Win Rate", value: fmtMaybeNumber(resultData.win_rate_pct, (n) => `${n.toFixed(1)}%`) },
                  { label: "Total Trades", value: fmtMaybeNumber(resultData.total_trades, (n) => String(Math.max(0, Math.floor(n)))) },
                  { label: "Profit Factor", value: fmtMaybeNumber(resultData.profit_factor, (n) => n.toFixed(2)) },
                  { label: "Avg Win", value: fmtMaybeNumber(resultData.avg_win, (n) => `₹${Math.round(n).toLocaleString("en-IN")}`), pnl: true },
                  { label: "Avg Loss", value: fmtMaybeNumber(resultData.avg_loss, (n) => `₹${Math.round(n).toLocaleString("en-IN")}`), neg: true },
                ].map((m: any) => (
                  <div key={m.label} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 14px" }}>
                    <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 6 }}>{m.label}</div>
                    <div style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700, color: m.pnl ? "var(--green)" : m.neg ? "var(--red)" : "var(--text)" }}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Charts + Trade log tabs */}
              <div className="card">
                <div style={{ display: "flex", gap: 2, marginBottom: 14 }}>
                  {(["equity", "trades", "monthly"] as const).map((t) => (
                    <button key={t} onClick={() => setActiveTab(t)} style={{
                      padding: "5px 14px", borderRadius: 4, border: "1px solid transparent",
                      cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
                      background: activeTab === t ? "var(--bg3)" : "transparent",
                      color: activeTab === t ? "var(--text)" : "var(--text3)",
                      borderColor: activeTab === t ? "var(--border)" : "transparent",
                    }}>
                      {t === "equity" ? "Equity Curve" : t === "trades" ? "Trade Log" : "Monthly P&L"}
                    </button>
                  ))}
                </div>

                {activeTab === "equity" && <EquityChart data={equityData} />}
                {activeTab === "trades" && <TradeTable trades={tradeData} />}
                {activeTab === "monthly" && <MonthlyBars />}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function EquityChart({ data }: { data: any[] }) {
  if (!Array.isArray(data) || data.length < 2) {
    return <div style={{ color: "var(--text3)", fontSize: 12 }}>No equity curve yet.</div>;
  }
  const W = 900, H = 180;
  const vals = data.map(d => Number(d?.value)).filter(isFiniteNumber);
  if (vals.length < 2) {
    return <div style={{ color: "var(--text3)", fontSize: 12 }}>No equity curve yet.</div>;
  }
  const mn = Math.min(...vals), mx = Math.max(...vals), rng = mx - mn || 1;
  const xs = vals.map((_, i) => (i / (vals.length - 1)) * W);
  const ys = vals.map(v => H - ((v - mn) / rng) * (H - 20) - 10);
  const path = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");
  const fill = `${path} L${W} ${H} L0 ${H} Z`;

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 180 }}>
        <defs>
          <linearGradient id="eq-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--green)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="var(--green)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={fill} fill="url(#eq-fill)" />
        <path d={path} fill="none" stroke="var(--green)" strokeWidth="2" />
        <circle cx={xs[xs.length-1]} cy={ys[ys.length-1]} r="4" fill="var(--green)" />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text3)", marginTop: 4 }}>
        <span>₹{Math.round(mn).toLocaleString()}</span>
        <span style={{ color: "var(--green)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>₹{Math.round(vals[vals.length-1]).toLocaleString()}</span>
        <span>₹{Math.round(mx).toLocaleString()}</span>
      </div>
    </div>
  );
}

function TradeTable({ trades }: { data?: unknown; trades: any[] }) {
  if (!Array.isArray(trades) || trades.length === 0) {
    return <div style={{ color: "var(--text3)", fontSize: 12 }}>No trades to show.</div>;
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="data-table">
        <thead><tr>
          <th>#</th><th>Side</th><th>Entry</th><th>Entry Price</th><th>Exit Price</th><th>P&L</th><th>P&L %</th><th>Bars</th><th>Exit Reason</th>
        </tr></thead>
        <tbody>
          {trades.map((t, i) => {
            const entryPrice = Number(t?.entry_price);
            const exitPrice = Number(t?.exit_price);
            const pnl = Number(t?.pnl);
            const pnlPct = Number(t?.pnl_pct);
            const exitReason = typeof t?.exit_reason === "string" ? t.exit_reason : "unknown";
            return (
            <tr key={t.id}>
              <td style={{ color: "var(--text3)" }}>{i + 1}</td>
              <td style={{ color: t.side === "long" ? "var(--green)" : "var(--red)", fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 11 }}>{t.side.toUpperCase()}</td>
              <td style={{ color: "var(--text3)" }}>{t.entry_time}</td>
              <td>{Number.isFinite(entryPrice) ? `₹${entryPrice.toFixed(2)}` : <span style={{ color: "var(--text3)" }}>N/A</span>}</td>
              <td>{Number.isFinite(exitPrice) ? `₹${exitPrice.toFixed(2)}` : <span style={{ color: "var(--text3)" }}>N/A</span>}</td>
              <td style={{ color: (Number.isFinite(pnl) ? pnl : 0) >= 0 ? "var(--green)" : "var(--red)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>
                {Number.isFinite(pnl) ? `${pnl >= 0 ? "+" : ""}₹${pnl.toFixed(0)}` : <span style={{ color: "var(--text3)" }}>N/A</span>}
              </td>
              <td style={{ color: (Number.isFinite(pnlPct) ? pnlPct : 0) >= 0 ? "var(--green)" : "var(--red)" }}>
                {Number.isFinite(pnlPct) ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : <span style={{ color: "var(--text3)" }}>N/A</span>}
              </td>
              <td style={{ color: "var(--text3)" }}>{t.bars_held}</td>
              <td>
                <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: "var(--bg3)", color: "var(--text3)" }}>
                  {exitReason.replaceAll("_", " ")}
                </span>
              </td>
            </tr>
          )})}
        </tbody>
      </table>
    </div>
  );
}

function MonthlyBars() {
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep"];
  const returns = [3.2, -1.1, 5.4, 2.8, -0.4, 4.1, -2.3, 6.7, 3.8];
  const max = Math.max(...returns.map(Math.abs));
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-end", height: 120 }}>
      {months.map((m, i) => (
        <div key={m} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 10, color: returns[i] >= 0 ? "var(--green)" : "var(--red)", fontFamily: "Syne, sans-serif", fontWeight: 600 }}>
            {returns[i] >= 0 ? "+" : ""}{returns[i]}%
          </span>
          <div style={{
            width: "100%", borderRadius: "3px 3px 0 0",
            height: `${Math.abs(returns[i]) / max * 70}px`,
            background: returns[i] >= 0 ? "rgba(0,212,160,0.5)" : "rgba(255,71,87,0.5)",
            border: `1px solid ${returns[i] >= 0 ? "var(--green)" : "var(--red)"}`,
          }} />
          <span style={{ fontSize: 10, color: "var(--text3)" }}>{m}</span>
        </div>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>{label}</label>
      {children}
    </div>
  );
}

const inputSt: React.CSSProperties = { background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", width: "100%" };
const ghostBtn: React.CSSProperties = { padding: "6px 13px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, cursor: "pointer" };
