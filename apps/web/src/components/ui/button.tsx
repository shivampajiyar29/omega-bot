import * as React from "react";

type Variant = "default" | "primary" | "danger" | "ghost" | "outline";
type Size    = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const VARIANT: Record<Variant, React.CSSProperties> = {
  default: { background: "var(--bg3)", border: "1px solid var(--border2)", color: "var(--text2)" },
  primary: { background: "var(--blue)", border: "1px solid var(--blue)", color: "#fff" },
  danger:  { background: "rgba(255,71,87,0.1)", border: "1px solid rgba(255,71,87,0.3)", color: "var(--red)" },
  ghost:   { background: "transparent", border: "1px solid transparent", color: "var(--text2)" },
  outline: { background: "transparent", border: "1px solid var(--border2)", color: "var(--text)" },
};

const SIZE: Record<Size, React.CSSProperties> = {
  sm: { padding: "4px 10px", fontSize: 11, borderRadius: 5 },
  md: { padding: "7px 16px", fontSize: 12, borderRadius: 6 },
  lg: { padding: "10px 22px", fontSize: 14, borderRadius: 8 },
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "default", size = "md", loading, icon, children, style, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        gap: 6, cursor: disabled || loading ? "not-allowed" : "pointer",
        fontFamily: "Syne, sans-serif", fontWeight: 500,
        opacity: disabled ? 0.5 : 1,
        transition: "all 0.13s",
        ...VARIANT[variant], ...SIZE[size], ...style,
      }}
      {...props}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  )
);
Button.displayName = "Button";

function Spinner() {
  return (
    <span style={{
      width: 12, height: 12, border: "1.5px solid currentColor",
      borderTopColor: "transparent", borderRadius: "50%",
      display: "inline-block", animation: "spin 0.7s linear infinite",
    }} />
  );
}
