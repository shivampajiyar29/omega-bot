"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard, LineChart, Eye, Braces, RefreshCcw,
  FileText, Zap, ClipboardList, Briefcase, Shield, BookOpen,
  Bell, Plug, Bot, Settings, Layers, ChevronRight,
} from "lucide-react";

const NAV = [
  {
    section: "Core",
    items: [
      { label: "Dashboard",       href: "/",             icon: LayoutDashboard },
      { label: "Charts",          href: "/charts",       icon: LineChart },
      { label: "Watchlist",       href: "/watchlist",    icon: Eye },
      { label: "Strategy Builder",href: "/strategy",     icon: Braces },
    ],
  },
  {
    section: "Trading",
    items: [
      { label: "Backtester",      href: "/backtest",     icon: RefreshCcw },
      { label: "Paper Trading",   href: "/paper",        icon: FileText },
      { label: "Live Trading",    href: "/live",         icon: Zap },
      { label: "Orders",          href: "/orders",       icon: ClipboardList },
      { label: "Positions",       href: "/positions",    icon: Briefcase },
    ],
  },
  {
    section: "Analytics",
    items: [
      { label: "Portfolio",       href: "/portfolio",    icon: Briefcase },
      { label: "Risk Center",     href: "/risk",         icon: Shield },
      { label: "Logs & Audit",    href: "/logs",         icon: BookOpen },
      { label: "Alerts",          href: "/alerts",       icon: Bell },
    ],
  },
  {
    section: "System",
    items: [
      { label: "Connectors",      href: "/connectors",   icon: Plug },
      { label: "AI Assistant",    href: "/ai",           icon: Bot },
      { label: "Module Manager",  href: "/modules",      icon: Layers },
      { label: "Settings",        href: "/settings",     icon: Settings },
    ],
  },
];

export function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: expanded ? 204 : 56,
        background: "var(--bg1)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        alignItems: expanded ? "flex-start" : "center",
        padding: "14px 0",
        flexShrink: 0,
        transition: "width 0.22s cubic-bezier(.4,0,.2,1)",
        overflowX: "hidden",
        overflowY: "auto",
        position: "relative",
        zIndex: 40,
      }}
    >
      {/* Logo */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: 34, height: 34,
          borderRadius: 8,
          background: "linear-gradient(135deg, #4a9eff, #9b8fff)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 15,
          color: "#fff", border: "none", cursor: "pointer",
          margin: expanded ? "0 0 18px 12px" : "0 0 18px 0",
          flexShrink: 0,
        }}
      >
        Ω
      </button>

      {/* Nav groups */}
      {NAV.map((group) => (
        <div key={group.section} style={{ width: "100%", marginTop: 8 }}>
          {expanded && (
            <div
              style={{
                fontSize: 9, textTransform: "uppercase", letterSpacing: "1.5px",
                color: "var(--text3)", fontFamily: "Syne, sans-serif",
                padding: "2px 12px 6px", fontWeight: 500,
              }}
            >
              {group.section}
            </div>
          )}
          {group.items.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: expanded ? "9px 12px" : "9px 0",
                  justifyContent: expanded ? "flex-start" : "center",
                  borderRadius: 6,
                  margin: expanded ? "1px 6px" : "1px auto",
                  width: expanded ? "calc(100% - 12px)" : 38,
                  color: active ? "var(--blue)" : "var(--text2)",
                  background: active ? "rgba(74,158,255,0.1)" : "transparent",
                  textDecoration: "none",
                  transition: "all 0.12s",
                  fontFamily: "Syne, sans-serif",
                  fontSize: 12,
                  fontWeight: 500,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                }}
                title={!expanded ? item.label : undefined}
              >
                <Icon size={16} style={{ flexShrink: 0 }} />
                {expanded && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>
      ))}

      {/* Expand toggle at bottom */}
      <div style={{ flex: 1 }} />
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          width: 28, height: 28, borderRadius: 6,
          background: "transparent", border: "1px solid var(--border)",
          color: "var(--text3)", cursor: "pointer",
          margin: expanded ? "4px 0 0 12px" : "4px 0 0 0",
          transition: "all 0.2s",
        }}
      >
        <ChevronRight
          size={14}
          style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
        />
      </button>
    </aside>
  );
}
