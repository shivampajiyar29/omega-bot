"use client";
import { useStore } from "@/store/useStore";

const MODULES = [
  {
    category: "Core (Always On)",
    locked: true,
    items: [
      { key: "dashboard",       label: "Dashboard",        desc: "Main overview and P&L summary" },
      { key: "watchlist",       label: "Watchlist",        desc: "Symbol watchlist with live prices" },
      { key: "charts",          label: "Charts",           desc: "Candlestick charts with indicators" },
      { key: "orders",          label: "Orders",           desc: "Order management and history" },
      { key: "positions",       label: "Positions",        desc: "Open and closed positions" },
      { key: "logs",            label: "Logs & Audit",     desc: "System and trade audit logs" },
      { key: "connectors",      label: "Connectors",       desc: "Broker and data API connections" },
      { key: "settings",        label: "Settings",         desc: "App configuration and preferences" },
    ],
  },
  {
    category: "Trading",
    locked: false,
    items: [
      { key: "strategy_builder",label: "Strategy Builder", desc: "Visual and DSL strategy creation" },
      { key: "backtester",      label: "Backtester",       desc: "Historical strategy backtesting" },
      { key: "paper_trading",   label: "Paper Trading",    desc: "Simulated trading with mock broker" },
      { key: "live_trading",    label: "Live Trading",     desc: "Real-money trading (use with caution)" },
      { key: "risk_management", label: "Risk Center",      desc: "Max loss guards and risk controls" },
      { key: "portfolio",       label: "Portfolio",        desc: "Portfolio tracking and equity curve" },
      { key: "alerts",          label: "Alerts",           desc: "Price and event notifications" },
    ],
  },
  {
    category: "Advanced (Optional)",
    locked: false,
    items: [
      { key: "ai_assistant",    label: "AI Assistant",     desc: "Generate and explain strategies with AI" },
      { key: "options_analytics",label:"Options Analytics",desc: "Greeks, IV, options chain viewer" },
      { key: "screener",        label: "Screener",         desc: "Multi-symbol strategy screener" },
      { key: "scanner",         label: "Scanner",          desc: "Real-time signal scanner" },
      { key: "trade_journal",   label: "Trade Journal",    desc: "Manual trade notes and analytics" },
      { key: "webhook_automation",label:"Webhook Automation",desc:"TradingView and external signal webhooks" },
    ],
  },
];

export default function ModulesPage() {
  const { enabledModules, toggleModule } = useStore();

  return (
    <div style={{ maxWidth: 860 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
          Module Manager
        </h1>
        <p style={{ color: "var(--text2)", fontSize: 12 }}>
          Enable only the features you need. Disabled modules are hidden from the sidebar and consume no resources.
        </p>
      </div>

      {MODULES.map((group) => (
        <div key={group.category} style={{ marginBottom: 28 }}>
          <div
            style={{
              fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
              textTransform: "uppercase", letterSpacing: "1.5px",
              color: "var(--text3)", marginBottom: 10,
            }}
          >
            {group.category}
          </div>

          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {group.items.map((mod, i) => {
              const enabled = group.locked ? true : (enabledModules[mod.key] ?? true);
              return (
                <div
                  key={mod.key}
                  style={{
                    display: "flex", alignItems: "center", gap: 14,
                    padding: "13px 16px",
                    borderBottom: i < group.items.length - 1 ? "1px solid var(--border)" : "none",
                    opacity: group.locked ? 0.7 : 1,
                  }}
                >
                  {/* Status dot */}
                  <div
                    style={{
                      width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                      background: enabled ? "var(--green)" : "var(--text3)",
                    }}
                  />

                  {/* Info */}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 500, color: "var(--text)" }}>
                      {mod.label}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 2 }}>
                      {mod.desc}
                    </div>
                  </div>

                  {/* Toggle */}
                  {group.locked ? (
                    <span
                      style={{
                        fontSize: 10, fontFamily: "Syne, sans-serif",
                        color: "var(--text3)", padding: "2px 8px",
                        border: "1px solid var(--border)", borderRadius: 4,
                      }}
                    >
                      REQUIRED
                    </span>
                  ) : (
                    <label className="toggle-wrap">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={() => toggleModule(mod.key)}
                      />
                      <span className="toggle-slider" />
                    </label>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <div
        style={{
          padding: "12px 16px",
          background: "rgba(74,158,255,0.06)",
          border: "1px solid rgba(74,158,255,0.15)",
          borderRadius: 8, fontSize: 11, color: "var(--text2)", lineHeight: 1.6,
        }}
      >
        <strong style={{ color: "var(--blue)", fontFamily: "Syne, sans-serif" }}>Adding new modules:</strong>{" "}
        Drop a new adapter into <code>/apps/api/app/adapters/</code> and register it in{" "}
        <code>/apps/api/app/connectors/registry.py</code>. Enable it here once added. No core code changes needed.
      </div>
    </div>
  );
}
