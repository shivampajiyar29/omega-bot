import * as React from "react";

// ─── Badge ────────────────────────────────────────────────────────────────────
type BadgeVariant = "green" | "red" | "amber" | "blue" | "purple" | "gray";

const BADGE_COLORS: Record<BadgeVariant, { bg: string; color: string; border: string }> = {
  green:  { bg: "rgba(0,212,160,0.1)",   color: "var(--green)",  border: "rgba(0,212,160,0.2)" },
  red:    { bg: "rgba(255,71,87,0.1)",   color: "var(--red)",    border: "rgba(255,71,87,0.2)" },
  amber:  { bg: "rgba(255,179,71,0.1)",  color: "var(--amber)",  border: "rgba(255,179,71,0.2)" },
  blue:   { bg: "rgba(74,158,255,0.1)",  color: "var(--blue)",   border: "rgba(74,158,255,0.2)" },
  purple: { bg: "rgba(155,143,255,0.1)", color: "var(--purple)", border: "rgba(155,143,255,0.2)" },
  gray:   { bg: "rgba(255,255,255,0.05)",color: "var(--text3)",  border: "var(--border)" },
};

interface BadgeProps { variant?: BadgeVariant; children: React.ReactNode; dot?: boolean; style?: React.CSSProperties }

export function Badge({ variant = "blue", children, dot, style }: BadgeProps) {
  const c = BADGE_COLORS[variant];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: dot ? 5 : 0,
      padding: "2px 8px", borderRadius: 4, fontSize: 10,
      fontFamily: "Syne, sans-serif", fontWeight: 500, letterSpacing: "0.3px",
      background: c.bg, color: c.color, border: `1px solid ${c.border}`, ...style,
    }}>
      {dot && <span style={{ width: 5, height: 5, borderRadius: "50%", background: c.color }} />}
      {children}
    </span>
  );
}

// ─── Input ────────────────────────────────────────────────────────────────────
export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & { label?: string }
>(({ label, style, ...props }, ref) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
    {label && (
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>
        {label}
      </label>
    )}
    <input
      ref={ref}
      style={{
        background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6,
        padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace",
        fontSize: 12, outline: "none", width: "100%", ...style,
      }}
      {...props}
    />
  </div>
));
Input.displayName = "Input";

// ─── Select ───────────────────────────────────────────────────────────────────
export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string }
>(({ label, children, style, ...props }, ref) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
    {label && (
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>
        {label}
      </label>
    )}
    <select
      ref={ref}
      style={{
        background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6,
        padding: "7px 10px", color: "var(--text)", fontFamily: "Syne, sans-serif",
        fontSize: 12, outline: "none", cursor: "pointer", width: "100%", ...style,
      }}
      {...props}
    >
      {children}
    </select>
  </div>
));
Select.displayName = "Select";

// ─── Table ────────────────────────────────────────────────────────────────────
interface Column<T> {
  key: string;
  header: string;
  width?: number;
  align?: "left" | "right" | "center";
  render?: (value: unknown, row: T) => React.ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  keyField?: keyof T;
}

export function Table<T extends Record<string, unknown>>({
  columns, data, onRowClick, emptyMessage = "No data", keyField,
}: TableProps<T>) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} style={{
                fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif",
                fontWeight: 500, textTransform: "uppercase", letterSpacing: "1px",
                padding: "6px 8px", textAlign: col.align ?? "left",
                borderBottom: "1px solid var(--border)",
                width: col.width,
              }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={{ padding: "24px 8px", textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={keyField ? String(row[keyField]) : i}
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? "pointer" : "default" }}
              >
                {columns.map(col => (
                  <td key={col.key} style={{
                    padding: "9px 8px", fontSize: 12, color: "var(--text2)",
                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                    textAlign: col.align ?? "left",
                  }}>
                    {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─── Toggle ───────────────────────────────────────────────────────────────────
export function Toggle({ checked, onChange, size = "md" }: { checked: boolean; onChange: () => void; size?: "sm" | "md" }) {
  const w = size === "sm" ? 26 : 32, h = size === "sm" ? 15 : 18, dot = size === "sm" ? 9 : 12;
  return (
    <div
      onClick={onChange}
      style={{
        width: w, height: h, borderRadius: h / 2, cursor: "pointer",
        position: "relative", transition: "background 0.2s",
        background: checked ? "rgba(0,212,160,0.3)" : "var(--border2)",
        border: `1px solid ${checked ? "rgba(0,212,160,0.5)" : "var(--border2)"}`,
        flexShrink: 0,
      }}
    >
      <span style={{
        position: "absolute", top: (h - dot) / 2, left: checked ? w - dot - (h - dot) / 2 : (h - dot) / 2,
        width: dot, height: dot, borderRadius: "50%",
        background: checked ? "var(--green)" : "var(--text3)",
        transition: "all 0.2s",
      }} />
    </div>
  );
}
