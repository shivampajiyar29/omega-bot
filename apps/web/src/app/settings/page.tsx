"use client";
import { useState } from "react";
import { toast } from "sonner";
import { useStore } from "@/store/useStore";

const RISK_DEFAULTS = {
  max_daily_loss: 5000,
  max_trade_loss: 1000,
  max_positions: 10,
  max_order_value: 50000,
  max_margin_pct: 80,
  trading_hours_start: "09:15",
  trading_hours_end: "15:15",
};

export default function SettingsPage() {
  const { tradingMode } = useStore();
  const [risk, setRisk] = useState(RISK_DEFAULTS);
  const [aiProvider, setAiProvider] = useState("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [notifyTelegram, setNotifyTelegram] = useState(false);
  const [telegramToken, setTelegramToken] = useState("");

  const save = () => toast.success("Settings saved");

  return (
    <div style={{ maxWidth: 780 }}>
      <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 24 }}>
        Settings
      </h1>

      {/* ── Risk Defaults ─────────────────────────────────────────────── */}
      <Section title="Risk Defaults">
        <p style={{ fontSize: 11, color: "var(--text3)", marginBottom: 14 }}>
          These apply globally unless overridden at the bot level.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {[
            { key: "max_daily_loss",   label: "Max Daily Loss (₹)" },
            { key: "max_trade_loss",   label: "Max Trade Loss (₹)" },
            { key: "max_positions",    label: "Max Open Positions" },
            { key: "max_order_value",  label: "Max Order Value (₹)" },
            { key: "max_margin_pct",   label: "Max Margin Usage (%)" },
          ].map(({ key, label }) => (
            <Field key={key} label={label}>
              <input
                type="number"
                value={risk[key as keyof typeof risk]}
                onChange={(e) => setRisk((r) => ({ ...r, [key]: Number(e.target.value) }))}
                style={inputStyle}
              />
            </Field>
          ))}
          <Field label="Trading Hours Start">
            <input
              type="time" value={risk.trading_hours_start}
              onChange={(e) => setRisk((r) => ({ ...r, trading_hours_start: e.target.value }))}
              style={inputStyle}
            />
          </Field>
          <Field label="Trading Hours End">
            <input
              type="time" value={risk.trading_hours_end}
              onChange={(e) => setRisk((r) => ({ ...r, trading_hours_end: e.target.value }))}
              style={inputStyle}
            />
          </Field>
        </div>
      </Section>

      {/* ── AI Assistant ────────────────────────────────────────────────── */}
      <Section title="AI Assistant">
        <p style={{ fontSize: 11, color: "var(--text3)", marginBottom: 14 }}>
          Powers the AI strategy generator. Your API key stays local, never sent anywhere except the AI provider.
        </p>
        <Field label="AI Provider">
          <select value={aiProvider} onChange={(e) => setAiProvider(e.target.value)} style={inputStyle}>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openai">OpenAI (GPT-4)</option>
          </select>
        </Field>
        <Field label="API Key" style={{ marginTop: 10 }}>
          <input
            type="password"
            placeholder="sk-ant-... or sk-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            style={inputStyle}
          />
        </Field>
      </Section>

      {/* ── Notifications ───────────────────────────────────────────────── */}
      <Section title="Notifications">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <label className="toggle-wrap">
            <input type="checkbox" checked={notifyTelegram} onChange={() => setNotifyTelegram(!notifyTelegram)} />
            <span className="toggle-slider" />
          </label>
          <span style={{ fontSize: 12, color: "var(--text)" }}>Telegram notifications</span>
        </div>
        {notifyTelegram && (
          <Field label="Bot Token">
            <input
              type="password"
              placeholder="1234567890:AAF..."
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              style={inputStyle}
            />
          </Field>
        )}
      </Section>

      {/* ── Trading Mode Warning ─────────────────────────────────────────── */}
      <Section title="Current Mode">
        <div
          style={{
            padding: "10px 14px", borderRadius: 7,
            background: tradingMode === "live" ? "rgba(255,71,87,0.08)" : "rgba(255,179,71,0.08)",
            border: `1px solid ${tradingMode === "live" ? "rgba(255,71,87,0.25)" : "rgba(255,179,71,0.25)"}`,
            fontSize: 12, color: tradingMode === "live" ? "var(--red)" : "var(--amber)",
          }}
        >
          {tradingMode === "live"
            ? "⚠️  LIVE mode is active. Real orders will be placed with real money."
            : "📄  PAPER mode is active. All trades are simulated. No real money at risk."}
        </div>
      </Section>

      {/* ── Data & Backup ───────────────────────────────────────────────── */}
      <Section title="Data & Backup">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { label: "Export Strategies",  action: () => toast.info("Exporting strategies…") },
            { label: "Export Trade Log",   action: () => toast.info("Exporting trade log…") },
            { label: "Backup Database",    action: () => toast.info("Starting backup…") },
            { label: "Restore Backup",     action: () => toast.info("Select a backup file…") },
          ].map(({ label, action }) => (
            <button key={label} onClick={action} style={btnStyle}>{label}</button>
          ))}
        </div>
      </Section>

      {/* ── Save ─────────────────────────────────────────────────────────── */}
      <button
        onClick={save}
        style={{
          marginTop: 8, padding: "9px 24px",
          background: "var(--blue)", color: "#fff",
          border: "none", borderRadius: 7,
          fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Save Settings
      </button>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div
        style={{
          fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600,
          color: "var(--text)", marginBottom: 14,
          paddingBottom: 10, borderBottom: "1px solid var(--border)",
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function Field({
  label, children, style,
}: {
  label: string; children: React.ReactNode; style?: React.CSSProperties;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, ...style }}>
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg3)",
  border: "1px solid var(--border2)",
  borderRadius: 6,
  padding: "7px 10px",
  color: "var(--text)",
  fontFamily: "IBM Plex Mono, monospace",
  fontSize: 12,
  outline: "none",
  width: "100%",
};

const btnStyle: React.CSSProperties = {
  padding: "7px 14px",
  background: "var(--bg3)",
  border: "1px solid var(--border2)",
  borderRadius: 6,
  color: "var(--text2)",
  fontFamily: "Syne, sans-serif",
  fontSize: 11, fontWeight: 500,
  cursor: "pointer",
};
