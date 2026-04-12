"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStore } from "@/store/useStore";
import {
  LayoutDashboard, LineChart, Eye, Braces, RefreshCcw,
  FileText, Zap, ClipboardList, Briefcase, Shield, BookOpen,
  Bell, Plug, Bot, Layers, Settings, Search, NotebookPen,
  BarChart3, Activity,
} from "lucide-react";

const NAV = [
  {
    group: "Trading",
    items: [
      { href: "/",          label: "Dashboard",      icon: LayoutDashboard },
      { href: "/charts",    label: "Charts",         icon: LineChart },
      { href: "/watchlist", label: "Watchlist",      icon: Eye },
      { href: "/paper",     label: "Paper Trading",  icon: FileText },
      { href: "/live",      label: "Live Trading",   icon: Zap },
      { href: "/orders",    label: "Orders",         icon: ClipboardList },
      { href: "/positions", label: "Positions",      icon: Briefcase },
    ],
  },
  {
    group: "Strategy & AI",
    items: [
      { href: "/strategy",   label: "Builder",       icon: Braces },
      { href: "/backtest",   label: "Backtester",    icon: RefreshCcw },
      { href: "/screener",   label: "Screener",      icon: Search },
      { href: "/indicators", label: "Indicators",    icon: Activity },
      { href: "/ai",         label: "AI Assistant",  icon: Bot },
    ],
  },
  {
    group: "Portfolio",
    items: [
      { href: "/portfolio",  label: "Portfolio",     icon: BarChart3 },
      { href: "/risk",       label: "Risk Center",   icon: Shield },
      { href: "/journal",    label: "Trade Journal", icon: NotebookPen },
    ],
  },
  {
    group: "System",
    items: [
      { href: "/connectors", label: "Connectors",   icon: Plug },
      { href: "/alerts",     label: "Alerts",       icon: Bell },
      { href: "/logs",       label: "Logs & Audit", icon: BookOpen },
      { href: "/modules",    label: "Modules",      icon: Layers },
      { href: "/settings",   label: "Settings",     icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { tradingMode } = useStore();
  const isLive = tradingMode === "live";

  return (
    <aside style={{
      width: 220, flexShrink: 0,
      background: "var(--bg1)",
      borderRight: "1px solid var(--border)",
      display: "flex", flexDirection: "column",
      height: "100vh", position: "sticky", top: 0,
      overflowY: "auto",
    }}>
      {/* Logo */}
      <div style={{
        padding: "18px 16px 14px",
        borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "linear-gradient(135deg, #4a9eff 0%, #9b8fff 100%)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, fontWeight: 800, color: "#fff",
          fontFamily: "Syne, sans-serif", flexShrink: 0,
        }}>Ω</div>
        <div>
          <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 15 }}>
            OmegaBot
          </div>
          <div style={{
            fontSize: 9, fontFamily: "Syne, sans-serif", fontWeight: 600,
            letterSpacing: "1.5px", textTransform: "uppercase",
            color: isLive ? "var(--red)" : "var(--amber)",
          }}>
            {isLive ? "● LIVE" : "● PAPER"}
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "10px 0" }}>
        {NAV.map(section => (
          <div key={section.group} style={{ marginBottom: 4 }}>
            <div style={{
              fontSize: 9, color: "var(--text3)",
              fontFamily: "Syne, sans-serif", fontWeight: 600,
              letterSpacing: "1.4px", textTransform: "uppercase",
              padding: "6px 16px 3px",
            }}>{section.group}</div>
            {section.items.map(item => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} style={{
                  display: "flex", alignItems: "center", gap: 9,
                  padding: "6px 16px",
                  textDecoration: "none",
                  borderRadius: "0 8px 8px 0",
                  marginRight: 8, marginBottom: 1,
                  background: active ? "rgba(74,158,255,0.1)" : "transparent",
                  borderLeft: active ? "2px solid var(--blue)" : "2px solid transparent",
                  color: active ? "var(--blue)" : "var(--text3)",
                  fontSize: 12,
                  fontFamily: "Syne, sans-serif",
                  fontWeight: active ? 600 : 400,
                  transition: "all 0.1s",
                }}>
                  <Icon size={14} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div style={{
        padding: "8px 16px",
        borderTop: "1px solid var(--border)",
        fontSize: 9, color: "var(--text3)",
        fontFamily: "IBM Plex Mono, monospace",
      }}>v1.0.0 · Personal use</div>
    </aside>
  );
}
