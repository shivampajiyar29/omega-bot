"use client";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";

type Message = { role: "user" | "assistant"; content: string; type?: "text" | "strategy" };

const SUGGESTIONS = [
  "Create an EMA crossover strategy for Nifty futures",
  "Explain what Sharpe ratio means for my backtest",
  "Build a mean reversion strategy using Bollinger Bands",
  "What risk settings should I use for intraday trading?",
  "Generate an RSI divergence strategy",
];

const WELCOME: Message = {
  role: "assistant",
  content: `Hi! I'm your trading strategy assistant. I can help you:

• **Generate strategies** from plain English descriptions
• **Explain backtest results** and what the metrics mean
• **Review and improve** existing strategies
• **Explain trading concepts** and risk management

To enable full AI capabilities, add your **ANTHROPIC_API_KEY** or **OPENAI_API_KEY** to the **.env** file.

Until then, I'll use built-in knowledge and sample strategies. What would you like to do?`,
};

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");

    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const res = await fetch("/api/v1/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      } else {
        // Fallback response
        setMessages((m) => [...m, { role: "assistant", content: getLocalResponse(msg) }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: getLocalResponse(msg) }]);
    } finally {
      setLoading(false);
    }
  };

  const generateStrategy = async () => {
    const desc = input.trim();
    if (!desc) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: `Generate a strategy for: ${desc}` }]);
    setLoading(true);

    try {
      const res = await fetch("/api/v1/ai/generate-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: desc }),
      });
      const data = await res.json();
      const strategyJson = JSON.stringify(data.strategy, null, 2);
      setMessages((m) => [...m, {
        role: "assistant",
        content: `Here's a strategy based on your description:\n\n\`\`\`json\n${strategyJson}\n\`\`\`\n\n${data.explanation}`,
        type: "strategy",
      }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: getLocalResponse(desc) }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 820, display: "flex", flexDirection: "column", height: "calc(100vh - 140px)" }}>
      {/* Header */}
      <div style={{ marginBottom: 16, flexShrink: 0 }}>
        <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>AI Assistant</h1>
        <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
          Generate strategies, explain results, and get trading guidance.
        </p>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, paddingBottom: 8 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "82%",
                padding: "11px 15px",
                borderRadius: m.role === "user" ? "12px 12px 4px 12px" : "12px 12px 12px 4px",
                background: m.role === "user"
                  ? "rgba(74,158,255,0.15)"
                  : "var(--bg2)",
                border: `1px solid ${m.role === "user" ? "rgba(74,158,255,0.25)" : "var(--border)"}`,
                fontSize: 12,
                color: "var(--text)",
                lineHeight: 1.65,
                fontFamily: "IBM Plex Mono, monospace",
                whiteSpace: "pre-wrap",
              }}
            >
              <MessageContent content={m.content} isStrategy={m.type === "strategy"} />
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: 6, padding: "12px 15px", maxWidth: 120, background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "12px 12px 12px 4px" }}>
            {[0, 1, 2].map((i) => (
              <span key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--text3)", display: "inline-block", animation: `pulse-dot 1.4s ease-in-out ${i * 0.15}s infinite` }} />
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 12, flexShrink: 0 }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} style={{ padding: "6px 12px", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 20, color: "var(--text2)", fontSize: 11, fontFamily: "Syne, sans-serif", cursor: "pointer" }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ flexShrink: 0, display: "flex", gap: 8, padding: "12px", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 10 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder="Describe a strategy, ask about metrics, or request an explanation… (Enter to send)"
          rows={2}
          style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, resize: "none", lineHeight: 1.5 }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <button onClick={() => send()} disabled={loading || !input.trim()} style={{ padding: "6px 16px", background: "var(--blue)", color: "#fff", border: "none", borderRadius: 6, fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600, cursor: "pointer", opacity: input.trim() ? 1 : 0.5 }}>
            Send
          </button>
          <button onClick={generateStrategy} disabled={loading || !input.trim()} style={{ padding: "6px 9px", background: "var(--bg3)", border: "1px solid var(--border2)", color: "var(--purple)", borderRadius: 6, fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500, cursor: "pointer", opacity: input.trim() ? 1 : 0.5 }}>
            ⟁ Gen DSL
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageContent({ content, isStrategy }: { content: string; isStrategy?: boolean }) {
  // Simple code block rendering
  const parts = content.split(/(```[\s\S]*?```)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          const code = part.replace(/```(?:json)?/, "").replace(/```$/, "").trim();
          return (
            <div key={i} style={{ margin: "8px 0" }}>
              <div style={{ background: "var(--bg1)", borderRadius: 6, padding: "10px 12px", overflow: "auto", fontSize: 11, border: "1px solid var(--border)" }}>
                <pre style={{ margin: 0, color: "var(--text)", fontFamily: "IBM Plex Mono, monospace" }}>{code}</pre>
              </div>
              {isStrategy && (
                <div style={{ display: "flex", gap: 7, marginTop: 8 }}>
                  <button onClick={() => toast.success("Strategy saved!")} style={{ padding: "5px 12px", background: "var(--blue)", border: "none", borderRadius: 5, color: "#fff", fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 600, cursor: "pointer" }}>
                    Save Strategy
                  </button>
                  <button onClick={() => toast.info("Opening in builder…")} style={{ padding: "5px 12px", background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 5, color: "var(--text2)", fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500, cursor: "pointer" }}>
                    Open in Builder
                  </button>
                </div>
              )}
            </div>
          );
        }
        return <span key={i}>{part.replace(/\*\*(.*?)\*\*/g, "$1")}</span>;
      })}
    </>
  );
}

function getLocalResponse(msg: string): string {
  const m = msg.toLowerCase();
  if (m.includes("sharpe")) return "Sharpe ratio measures risk-adjusted returns. A Sharpe > 1.0 is generally good, > 2.0 is excellent. It's calculated as (mean return - risk-free rate) / standard deviation. A higher Sharpe means you're getting more return per unit of risk taken.";
  if (m.includes("drawdown")) return "Max drawdown is the largest peak-to-trough decline in portfolio value. A max drawdown of 10% means at some point your portfolio dropped 10% from its all-time high before recovering. Lower is better — aim for < 15-20% for most strategies.";
  if (m.includes("ema")) return "EMA (Exponential Moving Average) gives more weight to recent prices. A common strategy is to buy when a fast EMA (e.g. 9-period) crosses above a slow EMA (e.g. 21-period). This signals upward momentum. Use the Strategy Builder to create an EMA crossover strategy.";
  if (m.includes("rsi")) return "RSI (Relative Strength Index) oscillates between 0-100. Values below 30 suggest oversold conditions (potential buy), above 70 suggest overbought (potential sell). Best used with a trend filter to avoid false signals in strongly trending markets.";
  return "I understand you're asking about " + msg + ". To get detailed AI responses, add your ANTHROPIC_API_KEY to the .env file. For now, try the Strategy Builder for creating strategies, or check the Backtester to test ideas.";
}
