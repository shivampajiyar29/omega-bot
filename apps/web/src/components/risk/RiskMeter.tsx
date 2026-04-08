"use client";

interface RiskMeterProps {
  label: string;
  current: number;
  max: number;
  unit?: string;
  color?: string;
  showNumbers?: boolean;
}

export function RiskMeter({ label, current, max, unit = "", color, showNumbers = true }: RiskMeterProps) {
  const pct = Math.min((current / max) * 100, 100);
  const autoColor = pct < 50 ? "var(--green)" : pct < 80 ? "var(--amber)" : "var(--red)";
  const barColor = color ?? autoColor;

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: "var(--text2)", fontFamily: "Syne, sans-serif" }}>{label}</span>
        {showNumbers && (
          <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace" }}>
            {unit}{current.toLocaleString("en-IN")} / {unit}{max.toLocaleString("en-IN")}
          </span>
        )}
      </div>
      <div style={{ height: 6, background: "var(--bg3)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: barColor, borderRadius: 3,
          transition: "width 0.6s ease, background 0.4s",
        }} />
      </div>
      <div style={{ textAlign: "right", fontSize: 9, color: "var(--text3)", marginTop: 3 }}>
        {pct.toFixed(1)}% used
      </div>
    </div>
  );
}

interface RiskDashboardProps {
  metrics: Array<{ label: string; current: number; max: number; unit?: string }>;
}

export function RiskDashboard({ metrics }: RiskDashboardProps) {
  return (
    <div>
      {metrics.map(m => (
        <RiskMeter key={m.label} {...m} />
      ))}
    </div>
  );
}
