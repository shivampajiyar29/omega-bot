"use client";
import React, { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";
import { useKillAllBots } from "@/hooks/useApi";
import { Power, Bell, Search, Loader2 } from "lucide-react";
import { toast } from "sonner";

export function Topbar() {
  const { tradingMode, setTradingMode, connectorStatus } = useStore();
  const killAll = useKillAllBots();
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
    }
  }, []);

  const handleKillSwitch = async () => {
    if (confirm("⚠️  Stop ALL active bots immediately? This will cancel pending orders and close all automated positions.")) {
      killAll.mutate(undefined, {
        onSuccess: () => {
          toast.success("Kill Switch Activated: All bots stopped.");
        },
        onError: (err: any) => {
          toast.error("Failed to execute Kill Switch. Manual intervention required.");
          console.error("Kill switch error:", err);
        }
      });
    }
  };

  return (
    <header
      style={{
        height: 52,
        background: "var(--bg1)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        gap: 14,
        flexShrink: 0,
      }}
    >
      {/* Search (decorative for now) */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: 8,
          background: "var(--bg3)", border: "1px solid var(--border)",
          borderRadius: 6, padding: "5px 12px", flex: 1, maxWidth: 320,
          cursor: "text",
        }}
      >
        <Search size={13} color="var(--text3)" />
        <span style={{ fontSize: 12, color: "var(--text3)" }}>Search symbols, strategies…</span>
        <span style={{
          marginLeft: "auto", fontSize: 10, color: "var(--text3)",
          background: "var(--bg2)", padding: "1px 6px", borderRadius: 3,
          border: "1px solid var(--border)",
        }}>⌘K</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Connector status */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "4px 10px", borderRadius: 5,
          background: connectorStatus === "connected" ? "rgba(0,212,160,0.08)" : "rgba(255,71,87,0.08)",
          border: `1px solid ${connectorStatus === "connected" ? "rgba(0,212,160,0.2)" : "rgba(255,71,87,0.2)"}`,
          fontSize: 10, fontFamily: "Syne, sans-serif", fontWeight: 500,
          color: connectorStatus === "connected" ? "var(--green)" : "var(--red)",
          cursor: "pointer",
        }}
      >
        <span
          className="dot-green animate-pulse-dot"
          style={{
            background: connectorStatus === "connected" ? "var(--green)" : "var(--red)",
          }}
        />
        {connectorStatus === "connected" ? "MOCK CONNECTED" : "DISCONNECTED"}
      </div>

      {/* Mode toggle */}
      <div
        style={{
          display: "flex", background: "var(--bg3)",
          border: "1px solid var(--border)", borderRadius: 6, padding: 3, gap: 2,
        }}
      >
        {(["paper", "live"] as const).map((m) => (
          <button
            key={m}
            onClick={() => {
              if (m === "live" && !confirm("Switch to LIVE trading mode? Real orders will be placed.")) return;
              setTradingMode(m);
            }}
            style={{
              padding: "4px 13px",
              borderRadius: 4,
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: 11, fontWeight: 500,
              border: "none", cursor: "pointer",
              transition: "all 0.12s",
              background:
                tradingMode === m
                  ? m === "paper"
                    ? "var(--amber)"
                    : "var(--red)"
                  : "transparent",
              color:
                tradingMode === m
                  ? m === "paper" ? "#0a0b0e" : "#fff"
                  : "var(--text2)",
            }}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Global Market Scope */}
      <div
        style={{
          display: "flex", background: "var(--bg3)",
          border: "1px solid var(--border)", borderRadius: 6, padding: 3, gap: 2,
        }}
      >
        {(["crypto", "indian", "american", "all"] as const).map((m) => (
          <button
            key={m}
            onClick={() => {
              setMarketScope(m);
              localStorage.setItem("omegabot_market_scope", m);
              toast.success(`Market scope: ${m}`);
            }}
            style={{
              padding: "4px 10px",
              borderRadius: 4,
              fontFamily: "Syne, sans-serif",
              fontSize: 10,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
              textTransform: "capitalize",
              background: marketScope === m ? "var(--bg1)" : "transparent",
              color: marketScope === m ? "var(--text)" : "var(--text3)",
            }}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Kill switch */}
      <button
        onClick={handleKillSwitch}
        title="Kill all bots"
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "5px 12px",
          background: "rgba(255,71,87,0.08)",
          border: "1px solid rgba(255,71,87,0.25)",
          borderRadius: 6, color: "var(--red)",
          fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
          cursor: "pointer", transition: "all 0.12s",
        }}
        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--red)";
          (e.currentTarget as HTMLButtonElement).style.color = "#fff";
        }}
        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => {
          (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,71,87,0.08)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--red)";
        }}
      >
        <Power size={13} />
        KILL ALL
      </button>

      {/* Alerts bell */}
      <button
        style={{
          width: 32, height: 32,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "var(--bg3)", border: "1px solid var(--border)",
          borderRadius: 6, color: "var(--text2)", cursor: "pointer",
          position: "relative",
        }}
      >
        <Bell size={14} />
        {/* Unread dot */}
        <span
          style={{
            position: "absolute", top: 5, right: 5,
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--red)", border: "1px solid var(--bg1)",
          }}
        />
      </button>

      {/* Avatar */}
      <div
        style={{
          width: 30, height: 30, borderRadius: "50%",
          background: "rgba(155,143,255,0.2)",
          border: "1px solid rgba(155,143,255,0.35)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600,
          color: "var(--purple)", cursor: "pointer",
        }}
      >
        U
      </div>
    </header>
  );
}
