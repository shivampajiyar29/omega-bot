"use client";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useBrokerConnectors, useMarketDataConnectors, useSetDefaultBroker } from "@/hooks/useApi";

export default function ConnectorsPage() {
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");
  const { data: brokersRaw = [], isLoading, error, refetch } = useBrokerConnectors();
  const { data: dataSourcesRaw = [], refetch: refetchDataSources } = useMarketDataConnectors();
  const setDefault = useSetDefaultBroker();
  const [activeConnector, setActiveConnector] = useState("mock");
  const [configuring, setConfiguring] = useState<string | null>(null);
  const BROKERS = brokersRaw.map((b: any) => ({
    name: b.name,
    label: b.display_name ?? b.name,
    desc: b.adapter_class ?? "Broker connector",
    status: b.status === "connected" ? "connected" : "disconnected",
    markets: (b.market_types ?? []).map((m: string) => m.toUpperCase()),
    configFields: [],
    isMock: b.name === "mock",
    is_default: b.is_default,
  }));
  const active = BROKERS.find((b: any) => b.is_default)?.label ?? "Mock Broker";
  const DATA_SOURCES = dataSourcesRaw.map((d: any) => ({
    name: d.name,
    label: d.display_name ?? d.name,
    desc: d.adapter_class ?? "Market data connector",
    status: d.status === "connected" ? "connected" : "disconnected",
    isMock: d.name === "mock",
  }));

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
    }
  }, []);

  const scopedBrokers = useMemo(() => {
    if (marketScope === "all") return BROKERS;
    if (marketScope === "crypto") return BROKERS.filter((b: any) => b.name === "binance" || b.markets.includes("CRYPTO"));
    if (marketScope === "indian") return BROKERS.filter((b: any) => ["groww","angel_one","upstox","zerodha","dhan"].includes(b.name));
    return BROKERS.filter((b: any) => ["alpaca","ibkr"].includes(b.name));
  }, [BROKERS, marketScope]);

  return (
    <div style={{ maxWidth: 900 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Connectors</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 4 }}>
          Connect to brokers and data providers. Each connector is pluggable — one adapter class per integration.
        </p>
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        {(["crypto", "indian", "american", "all"] as const).map((scope) => (
          <button
            key={scope}
            onClick={() => setMarketScope(scope)}
            style={{
              padding: "4px 10px",
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

      {/* Active connector */}
      <div style={{ padding: "10px 16px", background: "rgba(74,158,255,0.06)", border: "1px solid rgba(74,158,255,0.15)", borderRadius: 8, marginBottom: 24, fontSize: 12, color: "var(--blue)", display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--blue)", display: "inline-block" }} />
        <strong style={{ fontFamily: "Syne, sans-serif" }}>Active Broker:</strong>
        <span>{active}</span>
        <span style={{ color: "var(--text3)", marginLeft: "auto", fontSize: 11 }}>Switch by clicking "Set as Default" on any connected broker</span>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && (
        <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div style={{ color: "var(--red)", fontSize: 12 }}>Failed to load connectors (backend may be down)</div>
          <button
            onClick={() => { refetch(); refetchDataSources(); }}
            style={{ padding: "6px 10px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600 }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Broker section */}
      <SectionLabel>Broker Connectors</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28 }}>
        {scopedBrokers.map((b: any) => (
          <ConnectorCard
            key={b.name}
            item={b}
            isActive={activeConnector === b.name}
            onSetDefault={() => {
              setDefault.mutate(b.name, {
                onSuccess: () => {
                  setActiveConnector(b.name);
                  toast.success(`${b.label} set as active broker`);
                },
              });
            }}
            onConfigure={() => setConfiguring(configuring === b.name ? null : b.name)}
            isConfiguring={configuring === b.name}
          />
        ))}
        {scopedBrokers.length === 0 && (
          <div style={{ gridColumn: "1 / -1", color: "var(--text3)", fontSize: 12 }}>No brokers available for this scope yet.</div>
        )}
      </div>

      {/* Data section */}
      <SectionLabel>Market Data Sources</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {DATA_SOURCES.map((d: any) => (
          <DataCard key={d.name} item={d} />
        ))}
      </div>

      {/* Add custom */}
      <div style={{ marginTop: 24, padding: "14px 18px", border: "1px dashed var(--border2)", borderRadius: 10, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
        <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 500, marginBottom: 6 }}>+ Add Custom Connector</div>
        Create a new file at <code style={{ background: "var(--bg3)", padding: "1px 5px", borderRadius: 3 }}>apps/api/app/adapters/broker/your_broker.py</code>,
        subclass <code style={{ background: "var(--bg3)", padding: "1px 5px", borderRadius: 3 }}>BaseBrokerAdapter</code>, and it will appear here automatically.
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "1.5px", color: "var(--text3)", fontFamily: "Syne, sans-serif", fontWeight: 500, marginBottom: 10 }}>
      {children}
    </div>
  );
}

function ConnectorCard({ item, isActive, onSetDefault, onConfigure, isConfiguring }: any) {
  const connected = item.status === "connected";
  return (
    <div
      className="card"
      style={{ borderColor: isActive ? "rgba(74,158,255,0.3)" : "var(--border)" }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--bg3)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13, color: "var(--text2)", flexShrink: 0 }}>
          {item.label.slice(0, 2).toUpperCase()}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            {item.label}
            {isActive && <span style={{ fontSize: 9, padding: "1px 6px", background: "rgba(74,158,255,0.15)", color: "var(--blue)", borderRadius: 3, fontWeight: 500 }}>ACTIVE</span>}
          </div>
          <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 2 }}>{item.desc}</div>
        </div>
        <span style={{
          fontSize: 10, padding: "2px 8px", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 500, flexShrink: 0,
          background: connected ? "rgba(0,212,160,0.1)" : "rgba(255,255,255,0.05)",
          color: connected ? "var(--green)" : "var(--text3)",
          border: `1px solid ${connected ? "rgba(0,212,160,0.2)" : "var(--border)"}`,
        }}>
          {connected ? "● CONNECTED" : "○ DISCONNECTED"}
        </span>
      </div>

      {/* Market tags */}
      <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 12 }}>
        {item.markets?.map((m: string) => (
          <span key={m} style={{ fontSize: 10, padding: "2px 7px", background: "var(--bg3)", borderRadius: 4, color: "var(--text3)" }}>{m}</span>
        ))}
      </div>

      {/* Config form */}
      {isConfiguring && item.configFields?.length > 0 && (
        <div style={{ marginBottom: 12, padding: 12, background: "var(--bg3)", borderRadius: 8 }}>
          {item.configFields.map((f: string) => (
            <div key={f} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4 }}>{f}</div>
              <input type="password" placeholder={`Enter ${f}…`} style={{ width: "100%", background: "var(--bg1)", border: "1px solid var(--border2)", borderRadius: 5, padding: "6px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, outline: "none" }} />
            </div>
          ))}
          <button onClick={() => { onConfigure(); }} style={{ width: "100%", padding: "7px", background: "var(--blue)", border: "none", borderRadius: 6, color: "#fff", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600, cursor: "pointer", marginTop: 4 }}>
            Save & Test Connection
          </button>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 7 }}>
        {!item.isMock && (
          <button onClick={onConfigure} style={ghostBtn}>{isConfiguring ? "Cancel" : "Configure"}</button>
        )}
        {connected && !isActive && (
          <button onClick={onSetDefault} style={{ ...ghostBtn, color: "var(--blue)", borderColor: "rgba(74,158,255,0.3)" }}>Set as Default</button>
        )}
        {connected && (
          <button onClick={() => {}} style={ghostBtn}>Test</button>
        )}
      </div>
    </div>
  );
}

function DataCard({ item }: { item: any }) {
  const connected = item.status === "connected";
  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600 }}>{item.label}</div>
        <span style={{
          fontSize: 10, padding: "2px 8px", borderRadius: 4, fontFamily: "Syne, sans-serif", fontWeight: 500,
          background: connected ? "rgba(0,212,160,0.1)" : "rgba(255,255,255,0.05)",
          color: connected ? "var(--green)" : "var(--text3)",
          border: `1px solid ${connected ? "rgba(0,212,160,0.2)" : "var(--border)"}`,
        }}>{connected ? "● ON" : "○ OFF"}</span>
      </div>
      <div style={{ fontSize: 11, color: "var(--text3)" }}>{item.desc}</div>
    </div>
  );
}

const ghostBtn: React.CSSProperties = { padding: "5px 12px", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 5, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, cursor: "pointer" };
