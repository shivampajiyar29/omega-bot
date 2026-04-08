"use client";

import { useEffect, useMemo } from "react";
import TradingPage from "@/app/trading/page";
import { useStore } from "@/store/useStore";
import { useBrokerConnectors } from "@/hooks/useApi";

function StatusPill({ label, tone }: { label: string; tone: "good" | "bad" | "warn" }) {
  const st =
    tone === "good"
      ? { bg: "rgba(0,212,160,0.12)", bd: "rgba(0,212,160,0.25)", fg: "var(--green)" }
      : tone === "warn"
        ? { bg: "rgba(255,179,71,0.12)", bd: "rgba(255,179,71,0.25)", fg: "var(--amber)" }
        : { bg: "rgba(255,71,87,0.12)", bd: "rgba(255,71,87,0.25)", fg: "var(--red)" };
  return (
    <span
      style={{
        fontSize: 10,
        padding: "2px 8px",
        borderRadius: 999,
        background: st.bg,
        border: `1px solid ${st.bd}`,
        color: st.fg,
        fontFamily: "Syne, sans-serif",
        fontWeight: 700,
        letterSpacing: "0.6px",
        textTransform: "uppercase",
      }}
    >
      {label}
    </span>
  );
}

export default function LiveTradingRoute() {
  const { setTradingMode } = useStore();
  const { data: brokers = [], isLoading, error, refetch } = useBrokerConnectors();

  useEffect(() => {
    setTradingMode("live");
  }, [setTradingMode]);

  const liveDefault = useMemo(() => {
    const enabled = (brokers as any[]).find((b: any) => b.enabled);
    return enabled ?? (brokers as any[])[0] ?? null;
  }, [brokers]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        style={{
          background: "rgba(255,71,87,0.06)",
          border: "1px solid rgba(255,71,87,0.22)",
          borderRadius: 10,
          padding: "12px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, letterSpacing: "0.4px" }}>
            Live Mode
          </div>
          <div style={{ fontSize: 11, color: "var(--text3)" }}>
            Real orders may be sent to your broker. Verify connector + risk limits before trading.
          </div>
        </div>
        <StatusPill label="LIVE" tone="bad" />
      </div>

      <div className="card" style={{ padding: "12px 14px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div>
            <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>
              Broker connection
            </div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 650, marginTop: 4 }}>
              {isLoading ? "Checking…" : liveDefault ? (liveDefault.name ?? liveDefault.broker ?? "Broker") : "No broker connectors"}
            </div>
          </div>

          {error ? <StatusPill label="API error" tone="bad" /> : isLoading ? <StatusPill label="Loading" tone="warn" /> : liveDefault?.enabled ? <StatusPill label="Enabled" tone="good" /> : <StatusPill label="Not enabled" tone="warn" />}
        </div>

        {error && (
          <div style={{ marginTop: 10, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 11, color: "var(--red)" }}>Unable to load connectors. Backend may be down.</div>
            <button onClick={() => refetch()} style={{ padding: "6px 10px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      <TradingPage />
    </div>
  );
}
