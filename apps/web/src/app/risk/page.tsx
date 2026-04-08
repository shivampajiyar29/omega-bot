"use client";
import { useState } from "react";
import { toast } from "sonner";
import { useRiskDashboard, useRiskEvents, useRiskProfile } from "@/hooks/useApi";

export default function RiskPage() {
  const { data: riskProfile, isLoading, error } = useRiskProfile();
  const { data: riskDash } = useRiskDashboard();
  const { data: riskEvents = [] } = useRiskEvents(20);
  const [profile, setProfile] = useState({
    max_daily_loss: 5000,
    max_trade_loss: 1000,
    max_positions: 10,
    max_order_value: 50000,
    max_margin_pct: 80,
    start_time: "09:15",
    end_time: "15:15",
    blacklist: "",
    whitelist: "",
    kill_switch: false,
    max_loss_guard: true,
    margin_guard: true,
    duplicate_order_protection: true,
    time_window_filter: true,
  });
  const RISK_METRICS = [
    { label: "Daily Loss Used", current: Math.abs(Number(riskDash?.daily_pnl ?? 0)), limit: Number(riskDash?.daily_loss_limit ?? 5000), unit: "₹", color: "var(--green)", pct: Number(riskDash?.daily_loss_used_pct ?? 0) },
    { label: "Margin Used", current: Number(riskDash?.margin_used_pct ?? 0), limit: Number(riskDash?.max_margin_pct ?? 80), unit: "%", color: "var(--amber)", pct: Number(riskDash?.margin_used_pct ?? 0) },
    { label: "Open Positions", current: Number(riskDash?.open_positions ?? 0), limit: Number(riskDash?.max_positions ?? 10), unit: "", color: "var(--blue)", pct: Number(riskDash?.positions_used_pct ?? 0) },
    { label: "Order Value Today", current: Number(riskProfile?.max_order_value ?? 0), limit: Number(riskProfile?.max_order_value ?? 0), unit: "₹", color: "var(--purple)", pct: 100 },
  ];

  const update = (k: string, v: unknown) => setProfile((p) => ({ ...p, [k]: v }));
  const save = () => toast.success("Risk profile saved");
  const triggerKill = () => {
    if (confirm("⚠️  Activate kill switch? This will immediately stop ALL bots.")) {
      update("kill_switch", true);
      toast.error("Kill switch activated — all bots stopped");
    }
  };

  return (
    <div style={{ maxWidth: 960 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Risk Center</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
          Monitor live risk exposure and configure guardrails.
        </p>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && <div style={{ marginBottom: 12, color: "var(--red)", fontSize: 12 }}>Failed to load risk data</div>}

      {/* Live risk meters */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
        {RISK_METRICS.map((m) => (
          <div key={m.label} className="card">
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 8 }}>{m.label}</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 8 }}>
              <span style={{ fontFamily: "Syne, sans-serif", fontSize: 18, fontWeight: 700, color: "var(--text)" }}>
                {m.unit === "₹" ? `₹${m.current.toLocaleString("en-IN")}` : `${m.current}${m.unit}`}
              </span>
              <span style={{ fontSize: 11, color: "var(--text3)" }}>
                / {m.unit === "₹" ? `₹${m.limit.toLocaleString("en-IN")}` : `${m.limit}${m.unit}`}
              </span>
            </div>
            <div style={{ height: 5, background: "var(--bg3)", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${m.pct}%`, background: m.color, borderRadius: 3, transition: "width 0.5s" }} />
            </div>
            <div style={{ fontSize: 10, color: "var(--text3)", marginTop: 5, textAlign: "right" }}>{m.pct}% used</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Kill switch + Guards */}
        <div className="card">
          <SectionTitle>Emergency Controls</SectionTitle>

          {/* Kill switch */}
          <button
            onClick={triggerKill}
            style={{
              width: "100%", padding: "12px",
              background: profile.kill_switch ? "var(--red)" : "rgba(255,71,87,0.08)",
              border: "2px solid rgba(255,71,87,0.4)", borderRadius: 8,
              color: profile.kill_switch ? "#fff" : "var(--red)",
              fontFamily: "Syne, sans-serif", fontSize: 14, fontWeight: 700,
              cursor: "pointer", marginBottom: 16, letterSpacing: "0.5px",
            }}
          >
            ⊘ KILL ALL BOTS
          </button>

          {/* Guard toggles */}
          {[
            { key: "max_loss_guard", label: "Max Loss Guard", desc: "Stop bot if trade loss exceeds max_trade_loss" },
            { key: "margin_guard", label: "Margin Guard", desc: "Block orders if margin exceeds limit" },
            { key: "duplicate_order_protection", label: "Duplicate Order Protection", desc: "Prevent identical orders within 1 minute" },
            { key: "time_window_filter", label: "Trading Hours Filter", desc: "Only place orders in allowed time window" },
          ].map((g) => (
            <div key={g.key} style={{ display: "flex", alignItems: "center", gap: 12, paddingBottom: 12, marginBottom: 12, borderBottom: "1px solid var(--border)" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 500 }}>{g.label}</div>
                <div style={{ fontSize: 10, color: "var(--text3)", marginTop: 2 }}>{g.desc}</div>
              </div>
              <label className="toggle-wrap">
                <input type="checkbox" checked={profile[g.key as keyof typeof profile] as boolean} onChange={() => update(g.key, !profile[g.key as keyof typeof profile])} />
                <span className="toggle-slider" />
              </label>
            </div>
          ))}
        </div>

        {/* Limits config */}
        <div className="card">
          <SectionTitle>Risk Limits</SectionTitle>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <Field label="Max Daily Loss (₹)">
              <input type="number" value={profile.max_daily_loss} onChange={(e) => update("max_daily_loss", +e.target.value)} style={inputSt} />
            </Field>
            <Field label="Max Trade Loss (₹)">
              <input type="number" value={profile.max_trade_loss} onChange={(e) => update("max_trade_loss", +e.target.value)} style={inputSt} />
            </Field>
            <Field label="Max Open Positions">
              <input type="number" value={profile.max_positions} onChange={(e) => update("max_positions", +e.target.value)} style={inputSt} />
            </Field>
            <Field label="Max Order Value (₹)">
              <input type="number" value={profile.max_order_value} onChange={(e) => update("max_order_value", +e.target.value)} style={inputSt} />
            </Field>
            <Field label="Max Margin Usage (%)">
              <input type="number" value={profile.max_margin_pct} onChange={(e) => update("max_margin_pct", +e.target.value)} style={inputSt} />
            </Field>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
            <Field label="Start Time">
              <input type="time" value={profile.start_time} onChange={(e) => update("start_time", e.target.value)} style={inputSt} />
            </Field>
            <Field label="End Time">
              <input type="time" value={profile.end_time} onChange={(e) => update("end_time", e.target.value)} style={inputSt} />
            </Field>
          </div>

          <Field label="Symbol Blacklist (comma-separated)" style={{ marginTop: 10 }}>
            <input placeholder="SYMBOL1, SYMBOL2" value={profile.blacklist} onChange={(e) => update("blacklist", e.target.value)} style={inputSt} />
          </Field>

          <button onClick={save} style={{ marginTop: 14, width: "100%", padding: "9px", background: "var(--blue)", border: "none", borderRadius: 7, color: "#fff", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
            Save Risk Profile
          </button>
        </div>
      </div>

      {/* Recent risk events */}
      <div className="card" style={{ marginTop: 16 }}>
        <SectionTitle>Recent Risk Events</SectionTitle>
        {(riskEvents as any[]).map((e: any, i: number) => (
          <div key={i} style={{ display: "flex", gap: 12, padding: "9px 0", borderBottom: i < 2 ? "1px solid var(--border)" : "none" }}>
            <span style={{ fontSize: 10, color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace", minWidth: 40 }}>
              {e.occurred_at ? new Date(e.occurred_at).toLocaleTimeString("en-IN", { hour12: false }) : "--:--"}
            </span>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: e.severity === "high" ? "var(--red)" : e.severity === "medium" ? "var(--amber)" : "var(--blue)", flexShrink: 0, marginTop: 3 }} />
            <span style={{ fontSize: 11, color: "var(--text2)" }}>{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, marginBottom: 14, paddingBottom: 10, borderBottom: "1px solid var(--border)" }}>{children}</div>;
}

function Field({ label, children, style }: { label: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, ...style }}>
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>{label}</label>
      {children}
    </div>
  );
}

const inputSt: React.CSSProperties = {
  background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6,
  padding: "6px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace",
  fontSize: 12, outline: "none", width: "100%",
};
