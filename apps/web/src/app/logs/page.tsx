"use client";
import { useState } from "react";
import { useLogs } from "@/hooks/useApi";

const LEVEL_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  success: { color: "var(--green)",  bg: "rgba(0,212,160,0.08)",  border: "var(--green)" },
  info:    { color: "var(--blue)",   bg: "rgba(74,158,255,0.06)", border: "var(--blue)" },
  warn:    { color: "var(--amber)",  bg: "rgba(255,179,71,0.08)", border: "var(--amber)" },
  error:   { color: "var(--red)",    bg: "rgba(255,71,87,0.08)",  border: "var(--red)" },
};

export default function LogsPage() {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const { data: logsData = [], isLoading, error, refetch } = useLogs({ limit: 300 });
  const ALL_LOGS = logsData.map((l: any) => ({
    time: l.logged_at ? new Date(l.logged_at).toLocaleTimeString("en-IN", { hour12: false }) : "--:--:--",
    level: String(l.details?.level ?? "info").toLowerCase(),
    source: l.entity_type ?? "system",
    msg: l.details?.message ?? l.action ?? "",
  }));

  const filtered = ALL_LOGS.filter((l: any) => {
    if (filter !== "all" && l.level !== filter) return false;
    if (search && !l.msg.toLowerCase().includes(search.toLowerCase()) && !l.source.includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div style={{ maxWidth: 1000 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Logs & Audit</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>Complete record of all system events, trades, and signals.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="Search logs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "6px 12px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", width: 200 }}
          />
          <button style={{ padding: "6px 14px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, cursor: "pointer" }}>
            Export
          </button>
        </div>
      </div>

      {/* Level filter */}
      <div style={{ display: "flex", gap: 4, marginBottom: 14 }}>
        {["all", "info", "success", "warn", "error"].map((l) => {
          const s = LEVEL_STYLE[l] ?? { color: "var(--text2)", bg: "transparent", border: "var(--border)" };
          return (
            <button
              key={l}
              onClick={() => setFilter(l)}
              style={{
                padding: "4px 12px", borderRadius: 5, cursor: "pointer",
                fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
                textTransform: "uppercase", letterSpacing: "0.5px",
                border: `1px solid ${filter === l ? s.border : "var(--border)"}`,
                background: filter === l ? s.bg : "transparent",
                color: filter === l ? s.color : "var(--text3)",
              }}
            >
              {l}
            </button>
          );
        })}
        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text3)", alignSelf: "center" }}>
          {filtered.length} entries
        </span>
      </div>

      {/* Log feed */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {isLoading && <div style={{ padding: 16, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
        {error && (
          <div style={{ padding: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <div style={{ color: "var(--red)", fontSize: 12 }}>Failed to load logs (backend may be down)</div>
            <button
              onClick={() => refetch()}
              style={{ padding: "6px 10px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600 }}
            >
              Retry
            </button>
          </div>
        )}
        {filtered.map((log: any, i: number) => {
          const s = LEVEL_STYLE[log.level] ?? LEVEL_STYLE.info;
          return (
            <div
              key={i}
              style={{
                display: "flex", gap: 12, padding: "10px 16px",
                borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none",
                borderLeft: `3px solid ${s.border}`,
              }}
            >
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--text3)", minWidth: 64, flexShrink: 0 }}>
                {log.time}
              </span>
              <span style={{
                fontSize: 9, padding: "2px 7px", borderRadius: 3, alignSelf: "center",
                fontFamily: "Syne, sans-serif", fontWeight: 600, textTransform: "uppercase",
                letterSpacing: "0.5px", flexShrink: 0, minWidth: 56, textAlign: "center",
                background: s.bg, color: s.color, border: `1px solid ${s.border}30`,
              }}>
                {log.level}
              </span>
              <span style={{ fontSize: 10, color: "var(--text3)", minWidth: 120, flexShrink: 0, fontFamily: "IBM Plex Mono, monospace" }}>
                {log.source}
              </span>
              <span style={{ fontSize: 12, color: "var(--text2)", lineHeight: 1.5 }}>
                {log.msg}
              </span>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
            No log entries match your filter.
          </div>
        )}
      </div>
    </div>
  );
}
