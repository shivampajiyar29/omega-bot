"use client";
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { SAMPLE_STRATEGIES } from "./sampleStrategies";
import { useStrategies, useCreateStrategy, useDeleteStrategy } from "@/hooks/useApi";

const STEPS = ["Market", "Indicators", "Entry", "Exits", "Sizing", "Review"];
const TIMEFRAMES = ["1m","3m","5m","15m","30m","1h","2h","4h","1d","1w"];
const INDICATOR_TYPES = ["ema","sma","rsi","macd","bbands","atr","vwap","stoch","supertrend"];

// Helpers
function StepTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontFamily: "Syne, sans-serif", fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--text)" }}>{children}</div>;
}
function Field({ label, children, style }: { label: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, ...style }}>
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>{label}</label>
      {children}
    </div>
  );
}

export default function StrategyBuilderPage() {
  const { data: strategies, isLoading: loadingList } = useStrategies();
  const createStrategy = useCreateStrategy();
  const deleteStrategy = useDeleteStrategy();

  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<"wizard" | "dsl">("wizard");
  const [showBuilder, setShowBuilder] = useState(false);
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");

  const [strategy, setStrategy] = useState({
    name: "",
    description: "",
    market_type: "equity",
    timeframe: "15m",
    allow_short: false,
    indicators: [] as Array<{ id: string; type: string; params: Record<string, number> }>,
    entry_long: "",
    exits: [] as Array<{ type: string; value: string; unit: string }>,
    sizing_method: "fixed_value",
    sizing_value: "25000",
  });

  const [dslText, setDslText] = useState("");
  const [addingIndicator, setAddingIndicator] = useState(false);
  const [newInd, setNewInd] = useState({ type: "ema", period: 21 });

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
      if (saved === "crypto") setStrategy((s) => ({ ...s, market_type: "crypto" }));
      if (saved === "indian") setStrategy((s) => ({ ...s, market_type: "equity" }));
      if (saved === "american") setStrategy((s) => ({ ...s, market_type: "equity" }));
    }
  }, []);

  const updateStrategy = (k: string, v: unknown) =>
    setStrategy((s) => ({ ...s, [k]: v }));

  const addIndicator = () => {
    const id = `${newInd.type}${newInd.period}`;
    setStrategy((s: any) => ({
      ...s,
      indicators: [...s.indicators, { id, type: newInd.type, params: { period: newInd.period } }],
    }));
    setAddingIndicator(false);
  };

  const addExit = () => {
    setStrategy((s: any) => ({
      ...s,
      exits: [...s.exits, { type: "fixed_stop", value: "1.5", unit: "pct" }],
    }));
  };

  const handleSave = async () => {
    if (!strategy.name) { toast.error("Strategy needs a name"); return; }
    
    try {
      const dsl = mode === "dsl" ? JSON.parse(dslText) : {
        version: "1.0",
        name: strategy.name,
        market: { type: strategy.market_type, timeframe: strategy.timeframe },
        indicators: strategy.indicators,
        logic: { entry: strategy.entry_long, exits: strategy.exits },
        risk: { sizing: { method: strategy.sizing_method, value: Number(strategy.sizing_value) } }
      };

      await createStrategy.mutateAsync({
        name: strategy.name,
        description: strategy.description,
        market_type: strategy.market_type as any,
        dsl: dsl,
        tags: ["wizard"]
      });

      toast.success(`Strategy "${strategy.name}" saved`);
      setShowBuilder(false);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to save strategy");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this strategy?")) return;
    try {
      await deleteStrategy.mutateAsync(id);
      toast.success("Strategy deleted");
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  return (
    <div style={{ maxWidth: 900 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Strategy Manager</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 4 }}>
            Create and manage your trading algorithms.
          </p>
        </div>
        <button onClick={() => setShowBuilder(!showBuilder)} style={saveBtnStyle}>
          {showBuilder ? "View List" : "+ Create New Strategy"}
        </button>
      </div>

      {!showBuilder ? (
        /* ── Strategy List ────────────────────────────────────────────── */
        <div className="card">
          <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: 14, fontWeight: 600 }}>Active Strategies</h2>
            {loadingList && <span style={{ fontSize: 11, color: "var(--text3)" }}>Loading...</span>}
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                <th style={thStyle}>Name</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Created</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {strategies?.map((s: any) => (
                <tr key={s.id} style={{ borderBottom: "1px solid var(--border2)" }}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600 }}>{s.name}</div>
                    <div style={{ fontSize: 10, color: "var(--text3)" }}>{s.description || "No description"}</div>
                  </td>
                  <td style={tdStyle}><span style={badgeStyle}>{s.market_type}</span></td>
                  <td style={tdStyle}>
                    <span style={{ color: s.is_active ? "var(--green)" : "var(--text3)", fontSize: 11 }}>
                      ● {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={tdStyle}>{new Date(s.created_at).toLocaleDateString()}</td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", gap: 10 }}>
                      <button onClick={() => handleDelete(s.id)} style={{ color: "var(--red)", background: "none", border: "none", cursor: "pointer", fontSize: 11 }}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loadingList && strategies?.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: 40, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
                    No strategies found. Create your first one!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* ── Strategy Builder ─────────────────────────────────────────── */
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            <div style={{ display: "flex", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, padding: 3, gap: 2 }}>
              {(["wizard","dsl"] as const).map((m) => (
                <button key={m} onClick={() => setMode(m)} style={{
                  padding: "5px 14px", borderRadius: 4, border: "none", cursor: "pointer",
                  fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
                  background: mode === m ? "var(--bg1)" : "transparent",
                  color: mode === m ? "var(--text)" : "var(--text3)",
                }}>
                  {m === "wizard" ? "🧙 Wizard" : "{ } DSL"}
                </button>
              ))}
            </div>
            {mode === "dsl" && (
              <select
                onChange={(e) => {
                  if (e.target.value) setDslText(JSON.stringify(SAMPLE_STRATEGIES[e.target.value as keyof typeof SAMPLE_STRATEGIES], null, 2));
                }}
                style={{ ...selStyle, fontSize: 11, width: 140 }}
                defaultValue=""
              >
                <option value="" disabled>Load sample…</option>
                <option value="ema_crossover">EMA Crossover</option>
                <option value="rsi_breakout">RSI Breakout</option>
              </select>
            )}
          </div>

          {mode === "dsl" ? (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "Syne, sans-serif" }}>strategy.json</span>
                <div style={{ flex: 1 }} />
                <button onClick={handleSave} style={saveBtnStyle}>Save Strategy</button>
              </div>
              <textarea
                value={dslText}
                onChange={(e) => setDslText(e.target.value)}
                style={{
                  width: "100%", minHeight: 480,
                  background: "var(--bg1)", color: "var(--text)",
                  fontFamily: "IBM Plex Mono, monospace", fontSize: 12,
                  border: "none", outline: "none", padding: 16, resize: "vertical",
                  lineHeight: 1.7,
                }}
                spellCheck={false}
              />
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 16 }}>
              <div className="card" style={{ padding: 10, alignSelf: "start" }}>
                {STEPS.map((s, i) => (
                  <div key={s} onClick={() => setStep(i)} style={{
                    padding: "8px 12px", borderRadius: 6, cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 8,
                    background: step === i ? "rgba(74,158,255,0.1)" : "transparent",
                    color: step === i ? "var(--blue)" : step > i ? "var(--text2)" : "var(--text3)",
                    fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: step === i ? 600 : 400,
                    marginBottom: 2,
                  }}>
                    <span style={{
                      width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 10, background: step >= i ? "rgba(74,158,255,0.15)" : "var(--bg3)",
                      color: step >= i ? "var(--blue)" : "var(--text3)",
                    }}>{i + 1}</span>
                    {s}
                  </div>
                ))}
              </div>

              <div className="card">
                {step === 0 && (
                  <div>
                    <StepTitle>Market & Timeframe</StepTitle>
                    <Field label="Strategy Name">
                      <input value={strategy.name} onChange={(e) => updateStrategy("name", e.target.value)} placeholder="e.g. My EMA Strategy" style={inputStyle} />
                    </Field>
                    <Field label="Description" style={{ marginTop: 12 }}>
                      <textarea value={strategy.description} onChange={(e) => updateStrategy("description", e.target.value)} placeholder="What does this strategy do?" style={{ ...inputStyle, minHeight: 70, resize: "vertical" }} />
                    </Field>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
                      <Field label="Market Type">
                        <select value={strategy.market_type} onChange={(e) => updateStrategy("market_type", e.target.value)} style={selStyle}>
                          {["equity","futures","options","crypto","forex","commodity"].map((m) => (
                            <option key={m} value={m}>{m.charAt(0).toUpperCase()+m.slice(1)}</option>
                          ))}
                        </select>
                      </Field>
                      <Field label="Timeframe">
                        <select value={strategy.timeframe} onChange={(e) => updateStrategy("timeframe", e.target.value)} style={selStyle}>
                          {TIMEFRAMES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </Field>
                    </div>
                    <div style={{ marginTop: 8, fontSize: 10, color: "var(--text3)" }}>
                      Scope default: <span style={{ color: "var(--text2)", textTransform: "capitalize" }}>{marketScope}</span>
                    </div>
                  </div>
                )}
                {step === 1 && (
                  <div>
                    <StepTitle>Indicators</StepTitle>
                    {strategy.indicators.map((ind, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: "var(--bg3)", borderRadius: 6, marginBottom: 6 }}>
                        <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--blue)" }}>{ind.type.toUpperCase()}</span>
                        <span style={{ fontSize: 11, color: "var(--text3)" }}>({JSON.stringify(ind.params)})</span>
                        <div style={{ flex: 1 }} />
                        <button onClick={() => setStrategy((s: any) => ({ ...s, indicators: s.indicators.filter((_: any, j: any) => j !== i) }))} style={{ color: "var(--red)", background: "none", border: "none", cursor: "pointer" }}>✕</button>
                      </div>
                    ))}
                    <button onClick={() => setAddingIndicator(true)} style={{ ...ghostBtnStyle, marginTop: 8 }}>+ Add Indicator</button>
                    {addingIndicator && (
                       <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginTop: 10 }}>
                        <Field label="Type"><select value={newInd.type} onChange={(e) => setNewInd((n: any) => ({ ...n, type: e.target.value }))} style={selStyle}>{INDICATOR_TYPES.map(t => <option key={t} value={t}>{t}</option>)}</select></Field>
                        <Field label="Period"><input type="number" value={newInd.period} onChange={(e) => setNewInd((n: any) => ({ ...n, period: Number(e.target.value) }))} style={inputStyle} /></Field>
                        <button onClick={addIndicator} style={saveBtnStyle}>Add</button>
                       </div>
                    )}
                  </div>
                )}
                {step === 2 && (
                  <div>
                    <StepTitle>Entry Rules</StepTitle>
                    <Field label="Long Entry Condition (plain English)">
                      <textarea value={strategy.entry_long} onChange={(e) => updateStrategy("entry_long", e.target.value)} placeholder="e.g. Enter long when EMA9 crosses above EMA21" style={{ ...inputStyle, minHeight: 100 }} />
                    </Field>
                  </div>
                )}
                {step === 3 && (
                  <div>
                    <StepTitle>Exit Rules</StepTitle>
                    {strategy.exits.map((ex, i) => (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                        <Field label="Type"><select value={ex.type} onChange={(e) => { const exits = [...strategy.exits]; exits[i].type = e.target.value; updateStrategy("exits", exits); }} style={selStyle}><option value="fixed_stop">Stop Loss</option><option value="fixed_target">Take Profit</option></select></Field>
                        <Field label="Value"><input value={ex.value} onChange={(e) => { const exits = [...strategy.exits]; exits[i].value = e.target.value; updateStrategy("exits", exits); }} style={inputStyle} /></Field>
                        <button onClick={() => updateStrategy("exits", strategy.exits.filter((_: any, j: any) => j !== i))} style={{ color: "var(--red)", background: "none", border: "none" }}>✕</button>
                      </div>
                    ))}
                    <button onClick={addExit} style={ghostBtnStyle}>+ Add Exit</button>
                  </div>
                )}
                {step === 4 && (
                  <div>
                    <StepTitle>Position Sizing</StepTitle>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <Field label="Method"><select value={strategy.sizing_method} onChange={(e) => updateStrategy("sizing_method", e.target.value)} style={selStyle}><option value="fixed_value">Fixed Value (₹)</option><option value="fixed_qty">Fixed Quantity</option></select></Field>
                      <Field label="Value"><input type="number" value={strategy.sizing_value} onChange={(e) => updateStrategy("sizing_value", e.target.value)} style={inputStyle} /></Field>
                    </div>
                  </div>
                )}
                {step === 5 && (
                  <div>
                    <StepTitle>Review & Save</StepTitle>
                    <pre style={{ background: "var(--bg1)", padding: 14, borderRadius: 8, fontSize: 11, color: "var(--text2)", overflow: "auto", maxHeight: 200 }}>{JSON.stringify(strategy, null, 2)}</pre>
                    <button onClick={handleSave} style={{ ...saveBtnStyle, marginTop: 14, width: "100%" }}>💾 Save Strategy</button>
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
                  <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} style={ghostBtnStyle}>← Back</button>
                  {step < STEPS.length - 1 && <button onClick={() => setStep((s) => s + 1)} style={saveBtnStyle}>Next →</button>}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = { background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", width: "100%" };
const selStyle: React.CSSProperties = { ...inputStyle as object } as React.CSSProperties;
const saveBtnStyle: React.CSSProperties = { padding: "7px 18px", background: "var(--blue)", color: "#fff", border: "none", borderRadius: 6, fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, cursor: "pointer" };
const ghostBtnStyle: React.CSSProperties = { padding: "7px 14px", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500, cursor: "pointer" };
const thStyle: React.CSSProperties = { padding: "10px 12px", fontSize: 10, color: "var(--text3)", textTransform: "uppercase", letterSpacing: "1px" };
const tdStyle: React.CSSProperties = { padding: "12px", fontSize: 12, color: "var(--text2)" };
const badgeStyle: React.CSSProperties = { background: "var(--bg3)", padding: "2px 6px", borderRadius: 4, fontSize: 10, color: "var(--blue)", textTransform: "uppercase" };
