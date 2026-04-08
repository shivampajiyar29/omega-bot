"use client";
import { useState } from "react";
import { toast } from "sonner";
import { useAlerts, useDeleteAlert, useMarkAlertRead, useMarkAllAlertsRead } from "@/hooks/useApi";

const LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  critical: { color: "var(--red)",    bg: "rgba(255,71,87,0.08)",  border: "rgba(255,71,87,0.25)",  icon: "⊗" },
  warning:  { color: "var(--amber)",  bg: "rgba(255,179,71,0.08)", border: "rgba(255,179,71,0.25)", icon: "⚠" },
  info:     { color: "var(--blue)",   bg: "rgba(74,158,255,0.08)", border: "rgba(74,158,255,0.25)", icon: "ⓘ" },
  success:  { color: "var(--green)",  bg: "rgba(0,212,160,0.08)",  border: "rgba(0,212,160,0.25)",  icon: "✓" },
};

export default function AlertsPage() {
  const [filter, setFilter] = useState("all");
  const { data, isLoading, error } = useAlerts({ limit: 200 });
  const markReadMutation = useMarkAlertRead();
  const markAllReadMutation = useMarkAllAlertsRead();
  const deleteAlertMutation = useDeleteAlert();

  const alerts = (data ?? []).map((a: any) => ({
    id: a.id,
    level: String(a.level ?? "info"),
    title: a.title ?? a.action ?? "Alert",
    msg: a.message ?? a.msg ?? "",
    time: a.created_at ? new Date(a.created_at).toLocaleTimeString("en-IN", { hour12: false }) : (a.time ?? "--:--:--"),
    read: a.is_read ?? a.read ?? false,
    source: a.source ?? a.entity_type ?? "system",
  }));

  const unread = alerts.filter(a => !a.read).length;

  const markRead = (id: string) => {
    markReadMutation.mutate(id);
  };

  const markAllRead = () => {
    markAllReadMutation.mutate();
    toast.success("All alerts marked as read");
  };

  const dismiss = (id: string) => {
    deleteAlertMutation.mutate(id);
  };

  const filtered = alerts.filter(a => {
    if (filter === "unread") return !a.read;
    if (filter !== "all") return a.level === filter;
    return true;
  });

  return (
    <div style={{ maxWidth: 860 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Alerts</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
            {unread > 0 ? `${unread} unread alert${unread > 1 ? "s" : ""}` : "All alerts read"}
          </p>
        </div>
        <button
          onClick={markAllRead}
          style={{ padding: "6px 14px", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, cursor: "pointer" }}
        >
          Mark all read
        </button>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {["all", "unread", "critical", "warning", "info"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "4px 13px", borderRadius: 5, cursor: "pointer",
              fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
              textTransform: "capitalize",
              border: `1px solid ${filter === f ? (LEVEL_CONFIG[f]?.border ?? "rgba(74,158,255,0.3)") : "var(--border)"}`,
              background: filter === f ? (LEVEL_CONFIG[f]?.bg ?? "rgba(74,158,255,0.08)") : "transparent",
              color: filter === f ? (LEVEL_CONFIG[f]?.color ?? "var(--blue)") : "var(--text3)",
            }}
          >
            {f}
            {f === "unread" && unread > 0 && (
              <span style={{ marginLeft: 5, background: "var(--red)", color: "#fff", borderRadius: "50%", width: 14, height: 14, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 700 }}>
                {unread}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {isLoading && (
          <div style={{ textAlign: "center", padding: "20px 0", color: "var(--text3)", fontSize: 12 }}>Loading...</div>
        )}
        {error && (
          <div style={{ textAlign: "center", padding: "20px 0", color: "var(--red)", fontSize: 12 }}>Failed to load alerts</div>
        )}
        {filtered.map(a => {
          const cfg = LEVEL_CONFIG[a.level] ?? LEVEL_CONFIG.info;
          return (
            <div
              key={a.id}
              onClick={() => markRead(a.id)}
              style={{
                background: a.read ? "var(--bg2)" : cfg.bg,
                border: `1px solid ${a.read ? "var(--border)" : cfg.border}`,
                borderRadius: 10,
                padding: "14px 16px",
                display: "flex",
                gap: 14,
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {/* Icon */}
              <div style={{
                width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: cfg.bg, border: `1px solid ${cfg.border}`,
                color: cfg.color, fontSize: 16,
              }}>
                {cfg.icon}
              </div>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 13, color: "var(--text)" }}>
                    {a.title}
                  </span>
                  {!a.read && (
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.color, flexShrink: 0 }} />
                  )}
                  <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace", flexShrink: 0 }}>
                    {a.time}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text2)", lineHeight: 1.5 }}>{a.msg}</div>
                <div style={{ fontSize: 10, color: "var(--text3)", marginTop: 4 }}>Source: {a.source}</div>
              </div>

              {/* Dismiss */}
              <button
                onClick={e => { e.stopPropagation(); dismiss(a.id); }}
                style={{
                  alignSelf: "flex-start", background: "none", border: "none",
                  color: "var(--text3)", cursor: "pointer", fontSize: 14, padding: "0 2px",
                  opacity: 0.5, flexShrink: 0,
                }}
              >
                ✕
              </button>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text3)", fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🔔</div>
            No alerts to show.
          </div>
        )}
      </div>
    </div>
  );
}
