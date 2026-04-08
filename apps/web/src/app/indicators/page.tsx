"use client";
import { useState } from "react";
import { toast } from "sonner";
import { useCreateIndicator, useGenerateIndicator, useIndicators, useTestIndicator } from "@/hooks/useApi";

const TEMPLATE = `def compute(df, period=14):
    """
    Custom indicator template.
    
    Args:
        df: DataFrame with open, high, low, close, volume columns
        period: Lookback period
    
    Returns:
        pd.Series aligned to df.index
    """
    import pandas as pd
    close = df['close']
    
    # Your calculation here
    result = close.rolling(period).mean()
    
    return result`;

export default function IndicatorsPage() {
  const { data: indicators = [], isLoading, error } = useIndicators();
  const generateMutation = useGenerateIndicator();
  const testMutation = useTestIndicator();
  const createMutation = useCreateIndicator();
  const [activeTab, setActiveTab] = useState<"library" | "create" | "test">("library");
  const [code, setCode]           = useState(TEMPLATE);
  const [name, setName]           = useState("");
  const [desc, setDesc]           = useState("");
  const [outputType, setOutputType] = useState("line");
  const [color, setColor]         = useState("#4a9eff");
  const [aiPrompt, setAiPrompt]   = useState("");
  const [testResult, setTestResult] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [testing, setTesting]     = useState(false);
  const [saving, setSaving]       = useState(false);

  const generateWithAI = async () => {
    if (!aiPrompt.trim()) { toast.error("Describe the indicator"); return; }
    setGenerating(true);
    try {
      const data: any = await generateMutation.mutateAsync({ description: aiPrompt });
      if (data.code) {
        setCode(data.code);
        toast.success(`Generated with ${data.provider ?? "AI"} — review before saving`);
      } else {
        toast.error(data.error ?? "Generation failed");
      }
    } catch {
      toast.error("AI service unavailable");
    } finally {
      setGenerating(false);
    }
  };

  const testCode = async () => {
    setTesting(true);
    try {
      const data: any = await testMutation.mutateAsync({ code, bars: 50 });
      setTestResult(data);
      if (data.valid) toast.success("Indicator runs successfully");
      else toast.error(data.error ?? "Test failed");
    } catch {
      toast.error("Test request failed");
    } finally {
      setTesting(false);
    }
  };

  const saveIndicator = async () => {
    if (!name.trim()) { toast.error("Give the indicator a name"); return; }
    setSaving(true);
    try {
      await createMutation.mutateAsync({ name, description: desc, code, output_type: outputType, color });
        toast.success(`"${name}" saved — now available in charts!`);
        setActiveTab("library");
    } catch {
      toast.error("Save request failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 1060 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Custom Indicators</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
          Write Python indicator functions and add them to charts and strategy conditions.
        </p>
      </div>
      {isLoading && <div style={{ marginBottom: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
      {error && <div style={{ marginBottom: 12, color: "var(--red)", fontSize: 12 }}>Failed to load indicators</div>}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 3, marginBottom: 16, background: "var(--bg3)", padding: 4, borderRadius: 8, width: "fit-content" }}>
        {(["library", "create", "test"] as const).map(t => (
          <button key={t} onClick={() => setActiveTab(t)} style={{
            padding: "6px 18px", borderRadius: 5, border: "none", cursor: "pointer",
            fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 500,
            background: activeTab === t ? "var(--bg1)" : "transparent",
            color: activeTab === t ? "var(--text)" : "var(--text3)",
          }}>
            {t === "library" ? "📚 Library" : t === "create" ? "✏️ Create" : "🧪 Test"}
          </button>
        ))}
      </div>

      {/* ── Library ─────────────────────────────────────────────────────────── */}
      {activeTab === "library" && (
        <div>
          <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "1.2px", marginBottom: 12 }}>
            Built-in Indicators
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 24 }}>
            {(indicators as any[]).map((ind: any) => (
              <div key={ind.id} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: ind.color, flexShrink: 0 }} />
                  <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, fontSize: 13 }}>{ind.name}</div>
                  <span style={{ marginLeft: "auto", fontSize: 9, padding: "2px 7px", background: "var(--bg3)", borderRadius: 4, color: "var(--text3)", textTransform: "uppercase" }}>
                    {ind.type}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 12 }}>{ind.desc}</div>
                <div style={{ display: "flex", gap: 7 }}>
                  <button
                    onClick={() => { setCode(ind.code ?? `# ${ind.name}`); setName(ind.name); setActiveTab("create"); }}
                    style={btnGhost}
                  >
                    View Code
                  </button>
                  <button style={{ ...btnGhost, color: "var(--blue)", borderColor: "rgba(74,158,255,0.3)" }}>
                    Add to Chart
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: "14px 18px", border: "1px dashed var(--border2)", borderRadius: 10, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
            <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, marginBottom: 6, color: "var(--text)" }}>
              + Create Your Own
            </div>
            Write any technical indicator in Python. Uses pandas + numpy.
            AI can generate code from a description.{" "}
            <button onClick={() => setActiveTab("create")} style={{ color: "var(--blue)", background: "none", border: "none", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600 }}>
              Get started →
            </button>
          </div>
        </div>
      )}

      {/* ── Create ──────────────────────────────────────────────────────────── */}
      {activeTab === "create" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
          {/* Code editor */}
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
            {/* AI prompt bar */}
            <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", background: "var(--bg1)", display: "flex", gap: 8 }}>
              <input
                value={aiPrompt}
                onChange={e => setAiPrompt(e.target.value)}
                placeholder="Describe indicator in plain English (e.g. 'VWMA weighted by volume change')…"
                onKeyDown={e => e.key === "Enter" && generateWithAI()}
                style={{ flex: 1, background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 5, padding: "5px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, outline: "none" }}
              />
              <button
                onClick={generateWithAI}
                disabled={generating}
                style={{ padding: "5px 14px", background: "rgba(155,143,255,0.15)", border: "1px solid rgba(155,143,255,0.3)", borderRadius: 5, color: "var(--purple)", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600, cursor: "pointer", opacity: generating ? 0.6 : 1 }}
              >
                {generating ? "Generating…" : "⟁ AI Generate"}
              </button>
            </div>

            {/* Editor */}
            <div style={{ padding: "8px 14px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 10, color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace" }}>indicator.py</span>
              <div style={{ flex: 1 }} />
              <button onClick={testCode} disabled={testing} style={{ ...btnGhost, fontSize: 10, padding: "3px 10px" }}>
                {testing ? "Testing…" : "▶ Run Test"}
              </button>
            </div>
            <textarea
              value={code}
              onChange={e => setCode(e.target.value)}
              style={{
                width: "100%", minHeight: 420, background: "var(--bg1)", color: "var(--text)",
                fontFamily: "IBM Plex Mono, monospace", fontSize: 12, border: "none",
                outline: "none", padding: 16, resize: "vertical", lineHeight: 1.7,
                tabSize: 4,
              }}
              spellCheck={false}
            />

            {/* Test result */}
            {testResult && (
              <div style={{
                padding: "10px 14px", borderTop: "1px solid var(--border)",
                background: testResult.valid ? "rgba(0,212,160,0.05)" : "rgba(255,71,87,0.05)",
                fontSize: 11, fontFamily: "IBM Plex Mono, monospace",
              }}>
                {testResult.valid ? (
                  <span style={{ color: "var(--green)" }}>
                    ✓ Valid — Last value: <strong>{testResult.last}</strong> | Range: [{testResult.min}, {testResult.max}] | Non-null: {testResult.non_null}/{testResult.length}
                  </span>
                ) : (
                  <span style={{ color: "var(--red)" }}>✗ {testResult.error}</span>
                )}
              </div>
            )}
          </div>

          {/* Metadata panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
              <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, marginBottom: 14, paddingBottom: 10, borderBottom: "1px solid var(--border)" }}>
                Indicator Settings
              </div>

              <Field label="Name">
                <input value={name} onChange={e => setName(e.target.value)} placeholder="My RSI Variant" style={inputSt} />
              </Field>
              <Field label="Description" style={{ marginTop: 10 }}>
                <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="What does this indicator measure?" rows={3} style={{ ...inputSt, resize: "none" }} />
              </Field>
              <Field label="Output Type" style={{ marginTop: 10 }}>
                <select value={outputType} onChange={e => setOutputType(e.target.value)} style={inputSt}>
                  <option value="line">Line (overlay on price)</option>
                  <option value="histogram">Histogram (separate pane)</option>
                  <option value="signal">Signal (buy/sell dots)</option>
                </select>
              </Field>
              <Field label="Color" style={{ marginTop: 10 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="color" value={color} onChange={e => setColor(e.target.value)} style={{ width: 40, height: 32, border: "1px solid var(--border2)", borderRadius: 5, padding: 2, background: "var(--bg3)", cursor: "pointer" }} />
                  <input value={color} onChange={e => setColor(e.target.value)} style={{ ...inputSt, flex: 1 }} />
                </div>
              </Field>
            </div>

            {/* Info box */}
            <div style={{ padding: 14, background: "rgba(74,158,255,0.06)", border: "1px solid rgba(74,158,255,0.15)", borderRadius: 8, fontSize: 11, color: "var(--text2)", lineHeight: 1.7 }}>
              <strong style={{ color: "var(--blue)", fontFamily: "Syne, sans-serif" }}>Function signature:</strong>
              <br />
              <code style={{ fontSize: 10 }}>def compute(df, **params)</code>
              <br /><br />
              <strong style={{ color: "var(--blue)", fontFamily: "Syne, sans-serif" }}>df columns:</strong>
              <br />
              open, high, low, close, volume
              <br /><br />
              <strong style={{ color: "var(--blue)", fontFamily: "Syne, sans-serif" }}>Allowed imports:</strong>
              <br />
              pandas, numpy, math, statistics
            </div>

            <button
              onClick={saveIndicator}
              disabled={saving || !name}
              style={{ padding: "10px", background: "var(--blue)", border: "none", borderRadius: 8, color: "#fff", fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, cursor: "pointer", opacity: saving || !name ? 0.5 : 1 }}
            >
              {saving ? "Saving…" : "💾 Save Indicator"}
            </button>
          </div>
        </div>
      )}

      {/* ── Test ────────────────────────────────────────────────────────────── */}
      {activeTab === "test" && (
        <div style={{ maxWidth: 720 }}>
          <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10, padding: 16, marginBottom: 14 }}>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
              Quick Test — Paste Code
            </div>
            <textarea
              value={code}
              onChange={e => setCode(e.target.value)}
              rows={12}
              style={{ width: "100%", background: "var(--bg1)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", padding: 12, resize: "vertical", lineHeight: 1.7 }}
            />
            <button
              onClick={testCode}
              disabled={testing}
              style={{ marginTop: 10, padding: "8px 20px", background: "rgba(0,212,160,0.12)", border: "1px solid rgba(0,212,160,0.3)", borderRadius: 6, color: "var(--green)", fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
            >
              {testing ? "Running…" : "▶ Run on 50 Bars"}
            </button>
          </div>

          {testResult && (
            <div style={{ background: "var(--bg2)", border: `1px solid ${testResult.valid ? "rgba(0,212,160,0.3)" : "rgba(255,71,87,0.3)"}`, borderRadius: 10, padding: 16 }}>
              <div style={{ fontFamily: "Syne, sans-serif", fontSize: 12, fontWeight: 600, marginBottom: 12, color: testResult.valid ? "var(--green)" : "var(--red)" }}>
                {testResult.valid ? "✓ Test Passed" : "✗ Test Failed"}
              </div>
              {testResult.valid ? (
                <div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10, marginBottom: 14 }}>
                    {[["Last Value", testResult.last], ["Min", testResult.min], ["Max", testResult.max], ["Total Bars", testResult.length], ["Non-Null", testResult.non_null], ["Null %", `${((testResult.length - testResult.non_null) / testResult.length * 100).toFixed(1)}%`]].map(([k, v]) => (
                      <div key={k} style={{ background: "var(--bg3)", borderRadius: 6, padding: "8px 12px" }}>
                        <div style={{ fontSize: 9, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>{k}</div>
                        <div style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, marginTop: 4 }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text3)", marginBottom: 6 }}>Last 20 values:</div>
                  <div style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--text2)", lineHeight: 1.8 }}>
                    {testResult.output?.join(", ")}
                  </div>
                </div>
              ) : (
                <div style={{ color: "var(--red)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>{testResult.error}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, children, style }: { label: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, ...style }}>
      <label style={{ fontSize: 10, color: "var(--text3)", fontFamily: "Syne, sans-serif", textTransform: "uppercase", letterSpacing: "0.8px" }}>{label}</label>
      {children}
    </div>
  );
}

const inputSt: React.CSSProperties = {
  background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6,
  padding: "7px 10px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace",
  fontSize: 12, outline: "none", width: "100%",
};

const btnGhost: React.CSSProperties = {
  padding: "5px 12px", background: "var(--bg3)", border: "1px solid var(--border2)",
  borderRadius: 5, color: "var(--text2)", fontFamily: "Syne, sans-serif",
  fontSize: 11, fontWeight: 500, cursor: "pointer",
};
