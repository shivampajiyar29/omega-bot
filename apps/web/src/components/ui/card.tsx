import * as React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: string | number;
  noBorder?: boolean;
}

export function Card({ children, style, padding = 16, noBorder, ...props }: CardProps) {
  return (
    <div
      style={{
        background: "var(--bg2)",
        border: noBorder ? "none" : "1px solid var(--border)",
        borderRadius: 10,
        padding,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title, action, children,
}: { title?: string; action?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      {title && (
        <div style={{
          fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif",
          textTransform: "uppercase", letterSpacing: "1.2px", fontWeight: 500,
        }}>
          {title}
        </div>
      )}
      {children}
      {action}
    </div>
  );
}

export function StatCard({
  label, value, change, changeUp, color,
}: {
  label: string; value: string; change?: string; changeUp?: boolean; color?: string;
}) {
  return (
    <Card>
      <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontFamily: "Syne, sans-serif", fontSize: 22, fontWeight: 700, color: color ?? "var(--text)" }}>
        {value}
      </div>
      {change && (
        <div style={{ fontSize: 11, marginTop: 5, color: changeUp === true ? "var(--green)" : changeUp === false ? "var(--red)" : "var(--text3)" }}>
          {change}
        </div>
      )}
    </Card>
  );
}
