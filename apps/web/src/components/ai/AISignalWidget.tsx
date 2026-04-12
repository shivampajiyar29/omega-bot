"use client";
import { useEffect, useState, useCallback } from "react";

interface AISignal {
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number;
  agreement: boolean;
  xgb_signal: string;
  xgb_confidence: number;
  combined_score: number;
  reasoning: string;
  target_price: number;
  direction_pct: number;
  available: boolean;
  timestamp?: string;
}

interface Props {
  symbol: string;
  exchange?: string;
  timeframe?: string;
  compact?: boolean;
  autoRefreshMs?: number;
}

const CFG = {
  BUY:  { color: "var(--green)", bg: "rgba(0,212,160,0.1)",   border: "rgba(0,212,160,0.25)",  icon: "▲" },
  SELL: { color: "var(--red)",   bg: "rgba(255,71,87,0.1)",   border: "rgba(255,71,87,0.25)",  icon: "▼" },
  HOLD: { color: "var(--amber)", bg: "rgba(255,179,71,0.08)", border: "rgba(255,179,71,0.25)", icon: "◆" },
};

export function AISignalWidget({
  symbol, exchange = "NSE", timeframe = "15m",
  compact = false, autoRefreshMs = 0,
}: Props) {
  const [signal, setSignal]   = useState<AISignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  const fetch_ = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const r = await fetch(
        `/api/v1/ai-signal/quick/${symbol}?exchange=${exchange}&timeframe=${timeframe}`
      );
      if (r.ok) setSignal(await r.json());
    } catch {}
    finally { setLoading(false); }
  }, [symbol, exchange, timeframe]);

  useEffect(() => {
    fetch_();
    if (autoRefreshMs > 0) {
      const id = setInterval(fetch_, autoRefreshMs);
      return () => clearInterval(id);
    }
  }, [fetch_, autoRefreshMs]);

  if (loading && !signal) {
    return (
      <div style={{ display:"inline-flex", alignItems:"center", gap:6, padding:"4px 10px",
        background:"var(--bg3)", border:"1px solid var(--border)", borderRadius:6, fontSize:10, color:"var(--text3)" }}>
        <span style={{ width:7, height:7, borderRadius:"50%", background:"var(--text3)",
          display:"inline-block", animation:"pulse 1.4s infinite" }}/>
        Analysing {symbol}…
      </div>
    );
  }

  if (!signal) return null;

  const cfg = CFG[signal.signal] ?? CFG.HOLD;

  /* ── Compact badge ─────────────────────────────────────────────────────── */
  if (compact) {
    return (
      <div style={{ position:"relative", display:"inline-block" }}>
        <button
          onClick={() => setShowDetail(!showDetail)}
          title={signal.reasoning}
          style={{ display:"inline-flex", alignItems:"center", gap:5, padding:"3px 10px",
            borderRadius:5, cursor:"pointer", background:cfg.bg, border:`1px solid ${cfg.border}`,
            color:cfg.color, fontFamily:"Syne,sans-serif", fontSize:11, fontWeight:700 }}>
          <span>{cfg.icon}</span>
          <span>{signal.signal}</span>
          <span style={{ fontSize:10, opacity:0.8 }}>{(signal.confidence*100).toFixed(0)}%</span>
          {!signal.available && <span style={{ fontSize:9, opacity:0.6 }}>Tech</span>}
        </button>
        {showDetail && (
          <div style={{ position:"absolute", top:"calc(100% + 6px)", left:0, zIndex:200,
            background:"var(--bg2)", border:"1px solid var(--border2)", borderRadius:8,
            padding:"10px 14px", minWidth:240, boxShadow:"0 8px 24px rgba(0,0,0,0.4)",
            fontSize:11, fontFamily:"IBM Plex Mono,monospace", color:"var(--text2)", lineHeight:1.7 }}>
            <div style={{ marginBottom:6 }}>
              <span style={{ color:"var(--text3)" }}>XGBoost: </span>
              <span style={{ color:signal.xgb_signal==="UP"?"var(--green)":"var(--red)", fontWeight:600 }}>
                {signal.xgb_signal} ({(signal.xgb_confidence*100).toFixed(0)}%)
              </span>
            </div>
            {signal.target_price > 0 && (
              <div style={{ marginBottom:6 }}>
                <span style={{ color:"var(--text3)" }}>Target: </span>
                <span style={{ color:"var(--text)", fontWeight:600 }}>₹{signal.target_price}</span>
                <span style={{ color:signal.direction_pct>=0?"var(--green)":"var(--red)", marginLeft:6 }}>
                  ({signal.direction_pct>0?"+":""}{signal.direction_pct}%)
                </span>
              </div>
            )}
            <div style={{ borderTop:"1px solid var(--border)", paddingTop:6, marginTop:4,
              fontSize:10, color:"var(--text3)", lineHeight:1.6 }}>
              {signal.reasoning}
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ── Full card ─────────────────────────────────────────────────────────── */
  return (
    <div style={{ background:cfg.bg, border:`1px solid ${cfg.border}`, borderRadius:10, padding:16 }}>
      {/* Header row */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
        <div>
          <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif",
            textTransform:"uppercase", letterSpacing:"1.2px", marginBottom:4 }}>
            AI Signal · {symbol}
          </div>
          <div style={{ fontFamily:"Syne,sans-serif", fontSize:26, fontWeight:800,
            color:cfg.color, letterSpacing:"-0.5px" }}>
            {cfg.icon} {signal.signal}
          </div>
        </div>
        <div style={{ textAlign:"right" }}>
          <div style={{ fontFamily:"Syne,sans-serif", fontSize:32, fontWeight:800, color:cfg.color }}>
            {(signal.confidence*100).toFixed(0)}%
          </div>
          <div style={{ fontSize:10, color:"var(--text3)", marginTop:2 }}>confidence</div>
        </div>
      </div>

      {/* Model row */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:12 }}>
        {[
          { label:"XGBoost", sig:signal.xgb_signal, conf:signal.xgb_confidence, sub:"Pattern classifier" },
        ].map(m => (
          <div key={m.label} style={{ background:"var(--bg2)", borderRadius:8, padding:"10px 12px",
            border:"1px solid var(--border)" }}>
            <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif",
              textTransform:"uppercase", letterSpacing:"0.8px", marginBottom:4 }}>{m.label}</div>
            <div style={{ display:"flex", alignItems:"center", gap:6 }}>
              <span style={{ color:m.sig==="UP"?"var(--green)":"var(--red)",
                fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:14 }}>
                {m.sig==="UP"?"▲":"▼"} {m.sig}
              </span>
              <span style={{ fontSize:11, color:"var(--text3)" }}>
                {(m.conf*100).toFixed(0)}%
              </span>
            </div>
            <div style={{ fontSize:9, color:"var(--text3)", marginTop:2 }}>{m.sub}</div>
          </div>
        ))}

        {signal.target_price > 0 && (
          <div style={{ background:"var(--bg2)", borderRadius:8, padding:"10px 12px",
            border:"1px solid var(--border)" }}>
            <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"Syne,sans-serif",
              textTransform:"uppercase", letterSpacing:"0.8px", marginBottom:4 }}>Target Price</div>
            <div style={{ fontFamily:"Syne,sans-serif", fontWeight:700, fontSize:14 }}>
              ₹{signal.target_price}
            </div>
            <div style={{ fontSize:11, color:signal.direction_pct>=0?"var(--green)":"var(--red)", marginTop:2 }}>
              {signal.direction_pct>0?"+":""}{signal.direction_pct}%
            </div>
          </div>
        )}
      </div>

      {/* Status badge */}
      {!signal.available && (
        <div style={{ padding:"6px 10px", background:"rgba(255,179,71,0.08)",
          border:"1px solid rgba(255,179,71,0.2)", borderRadius:6, marginBottom:10,
          fontSize:10, color:"var(--amber)" }}>
          ⚠ AI Engine offline — showing technical signal only
        </div>
      )}

      {/* Reasoning */}
      <div style={{ fontSize:11, color:"var(--text3)", lineHeight:1.6,
        fontFamily:"IBM Plex Mono,monospace" }}>{signal.reasoning}</div>

      {/* Footer */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginTop:12 }}>
        <span style={{ fontSize:9, color:"var(--text3)" }}>
          {signal.timestamp ? new Date(signal.timestamp).toLocaleTimeString() : ""}
        </span>
        <button onClick={fetch_} disabled={loading}
          style={{ fontSize:10, padding:"3px 10px", background:"var(--bg3)",
            border:"1px solid var(--border)", borderRadius:5, color:"var(--text3)",
            cursor:"pointer", fontFamily:"Syne,sans-serif" }}>
          {loading ? "…" : "↺ Refresh"}
        </button>
      </div>
    </div>
  );
}
