"use client";
import { useState } from "react";
import { toast } from "sonner";

// ─── BotCard ──────────────────────────────────────────────────────────────────
export interface BotData {
  id: string;
  name: string;
  symbol: string;
  exchange?: string;
  status: "running" | "paused" | "stopped" | "error";
  pnl: number;
  trades?: number;
  signals?: number;
  strategy_name?: string;
}

interface BotCardProps {
  bot: BotData;
  onStart?: (id: string) => void;
  onPause?: (id: string) => void;
  onStop?:  (id: string) => void;
  compact?: boolean;
}

const STATUS_DOT: Record<string, string> = {
  running: "var(--green)",
  paused:  "var(--amber)",
  stopped: "var(--text3)",
  error:   "var(--red)",
};

export function BotCard({ bot, onStart, onPause, onStop, compact }: BotCardProps) {
  const isRunning = bot.status === "running";
  const isPaused  = bot.status === "paused";
  const isStopped = bot.status === "stopped";

  return (
    <div style={{
      background: "var(--bg2)",
      border: `1px solid ${isRunning ? "rgba(0,212,160,0.2)" : "var(--border)"}`,
      borderRadius: 10, padding: compact ? "10px 12px" : "14px 16px",
      transition: "border-color 0.2s",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: compact ? 8 : 12 }}>
        <span style={{
          width: 9, height: 9, borderRadius: "50%", flexShrink: 0,
          background: STATUS_DOT[bot.status] ?? "var(--text3)",
          boxShadow: isRunning ? "0 0 7px var(--green)" : "none",
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {bot.name}
          </div>
          <div style={{ fontSize: 10, color: "var(--text3)", marginTop: 1 }}>
            {bot.symbol} {bot.exchange ? `· ${bot.exchange}` : ""} · {bot.status.toUpperCase()}
          </div>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 16, color: bot.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
            {bot.pnl >= 0 ? "+" : ""}₹{bot.pnl.toLocaleString("en-IN")}
          </div>
          {!compact && bot.trades !== undefined && (
            <div style={{ fontSize: 10, color: "var(--text3)" }}>
              {bot.trades} trades · {bot.signals ?? 0} signals
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {!compact && (
        <div style={{ height: 4, background: "var(--bg3)", borderRadius: 2, marginBottom: 12, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 2, transition: "width 0.5s ease",
            width: `${Math.min(Math.abs(bot.pnl) / 50, 100)}%`,
            background: bot.pnl >= 0 ? "var(--green)" : "var(--red)",
          }} />
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 7 }}>
        {(isRunning || isPaused) && (
          <ActionBtn
            onClick={() => isPaused ? onStart?.(bot.id) : onPause?.(bot.id)}
            color={isPaused ? "green" : "amber"}
          >
            {isPaused ? "▶ Resume" : "⏸ Pause"}
          </ActionBtn>
        )}
        {isStopped && (
          <ActionBtn onClick={() => onStart?.(bot.id)} color="green">▶ Start</ActionBtn>
        )}
        {!isStopped && (
          <ActionBtn onClick={() => onStop?.(bot.id)} color="red">⊘ Stop</ActionBtn>
        )}
      </div>
    </div>
  );
}

function ActionBtn({ onClick, color, children }: { onClick?: () => void; color: string; children: React.ReactNode }) {
  const colors: Record<string, { bg: string; border: string; text: string }> = {
    green:  { bg: "rgba(0,212,160,0.1)",  border: "rgba(0,212,160,0.3)",  text: "var(--green)" },
    amber:  { bg: "rgba(255,179,71,0.1)", border: "rgba(255,179,71,0.3)", text: "var(--amber)" },
    red:    { bg: "rgba(255,71,87,0.1)",  border: "rgba(255,71,87,0.3)",  text: "var(--red)"   },
    default:{ bg: "var(--bg3)",           border: "var(--border2)",       text: "var(--text2)" },
  };
  const c = colors[color] ?? colors.default;
  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 13px", borderRadius: 5, cursor: "pointer",
        fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
        background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      }}
    >
      {children}
    </button>
  );
}

// ─── QuickOrder ───────────────────────────────────────────────────────────────
interface QuickOrderProps {
  defaultSymbol?: string;
  onSubmit?: (order: { symbol: string; side: "buy" | "sell"; qty: number; price?: number }) => void;
}

export function QuickOrder({ defaultSymbol = "", onSubmit }: QuickOrderProps) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [qty,    setQty]    = useState("1");
  const [price,  setPrice]  = useState("");
  const [type,   setType]   = useState<"market" | "limit">("market");

  const submit = (side: "buy" | "sell") => {
    if (!symbol) { toast.error("Enter a symbol"); return; }
    const q = parseFloat(qty);
    if (!q || q <= 0) { toast.error("Invalid quantity"); return; }
    onSubmit?.({ symbol: symbol.toUpperCase(), side, qty: q, price: price ? parseFloat(price) : undefined });
    toast.success(`${side.toUpperCase()} ${qty} ${symbol.toUpperCase()} (${type})`);
  };

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
        <div>
          <Label>Symbol</Label>
          <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} placeholder="RELIANCE" style={inputSt} />
        </div>
        <div>
          <Label>Quantity</Label>
          <input type="number" value={qty} onChange={e => setQty(e.target.value)} min="1" style={inputSt} />
        </div>
        <div>
          <Label>Type</Label>
          <select value={type} onChange={e => setType(e.target.value as any)} style={inputSt}>
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </div>
        {type === "limit" && (
          <div>
            <Label>Price</Label>
            <input type="number" value={price} onChange={e => setPrice(e.target.value)} placeholder="0.00" style={inputSt} />
          </div>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <button
          onClick={() => submit("buy")}
          style={{ padding: "9px", background: "rgba(0,212,160,0.12)", border: "1px solid rgba(0,212,160,0.3)", borderRadius: 6, color: "var(--green)", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 700, cursor: "pointer" }}
        >▲ BUY</button>
        <button
          onClick={() => submit("sell")}
          style={{ padding: "9px", background: "rgba(255,71,87,0.12)", border: "1px solid rgba(255,71,87,0.3)", borderRadius: 6, color: "var(--red)", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 700, cursor: "pointer" }}
        >▼ SELL</button>
      </div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.8px" }}>{children}</div>;
}

const inputSt: React.CSSProperties = {
  width: "100%", background: "var(--bg3)", border: "1px solid var(--border2)",
  borderRadius: 6, padding: "7px 10px", color: "var(--text)",
  fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none",
};
