"use client";
import { useEffect, useMemo, useState } from "react";
import { useAddWatchlistSymbol, useInstrumentSearch, useRemoveWatchlistSymbol, useWatchlist } from "@/hooks/useApi";

export default function WatchlistPage() {
  const [marketScope, setMarketScope] = useState<"all" | "indian" | "crypto" | "american">("crypto");
  const [sortBy, setSortBy] = useState<"name"|"price"|"chg">("name");
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const { data: watchlist, isLoading, error } = useWatchlist();
  const addSymbolMutation = useAddWatchlistSymbol();
  const removeSymbolMutation = useRemoveWatchlistSymbol();
  const marketType = marketScope === "crypto" ? "crypto" : marketScope === "indian" ? "equity" : marketScope === "american" ? "equity" : "crypto";
  const { data: searchResultsRaw = [] } = useInstrumentSearch(search, marketType);

  useEffect(() => {
    const saved = (localStorage.getItem("omegabot_market_scope") || "").toLowerCase();
    if (saved === "all" || saved === "indian" || saved === "crypto" || saved === "american") {
      setMarketScope(saved);
    }
  }, []);

  const items = useMemo(() => {
    const symbols = watchlist?.symbols ?? [];
    return symbols.map((s, idx) => {
      const base = 1000 + (idx + 1) * 123;
      return {
        ticker: s.symbol,
        name: s.symbol,
        exchange: s.exchange,
        type: s.market_type,
        price: base,
        day_high: +(base * 1.01).toFixed(2),
        day_low: +(base * 0.99).toFixed(2),
        volume: 0,
      };
    });
  }, [watchlist]);

  const SEARCH_RESULTS = searchResultsRaw
    .filter((r: any) => {
      if (marketScope === "crypto") return (r.exchange ?? "").toUpperCase() === "BINANCE" || String(r.symbol || "").endsWith("USDT");
      if (marketScope === "indian") return ["NSE", "BSE"].includes((r.exchange ?? "").toUpperCase());
      if (marketScope === "american") return ["NYSE", "NASDAQ", "ARCA", "AMEX"].includes((r.exchange ?? "").toUpperCase());
      return true;
    })
    .map((r: any) => ({
    ticker: r.symbol,
    name: r.name ?? r.symbol,
    exchange: r.exchange ?? "NSE",
    type: r.market_type ?? "equity",
  }));

  const addSymbol = (sym: { ticker: string; exchange: string; type: string }) => {
    addSymbolMutation.mutate({ symbol: sym.ticker, exchange: sym.exchange, market_type: sym.type });
    setSearch(""); setShowSearch(false);
  };

  const removeSymbol = (ticker: string) => {
    removeSymbolMutation.mutate(ticker);
  };

  const sorted = [...items].sort((a, b) => {
    if (sortBy === "price") return b.price - a.price;
    if (sortBy === "name")  return a.ticker.localeCompare(b.ticker);
    return 0;
  });

  return (
    <div style={{ maxWidth: 1000 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Watchlist</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>
            {items.length} symbols tracked · Prices refresh every 2s
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, position: "relative" }}>
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setShowSearch(true); }}
            onFocus={() => setShowSearch(true)}
            placeholder="Search symbol to add…"
            style={{ background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "7px 12px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", width: 220 }}
          />
          {showSearch && search && (
            <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "var(--bg2)", border: "1px solid var(--border2)", borderRadius: 8, zIndex: 50, marginTop: 4, overflow: "hidden", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
              {SEARCH_RESULTS.filter((r: any) => r.ticker.includes(search.toUpperCase()) || r.name.toLowerCase().includes(search.toLowerCase())).map((r: any) => (
                <div key={r.ticker} onClick={() => addSymbol(r)} style={{ padding: "10px 14px", cursor: "pointer", display: "flex", gap: 10, alignItems: "center" }}
                  onMouseEnter={(e: any) => (e.currentTarget.style.background = "var(--bg3)")}
                  onMouseLeave={(e: any) => (e.currentTarget.style.background = "transparent")}>
                  <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13, width: 80 }}>{r.ticker}</span>
                  <span style={{ fontSize: 11, color: "var(--text3)", flex: 1 }}>{r.name}</span>
                  <span style={{ fontSize: 10, padding: "1px 6px", background: "var(--bg3)", borderRadius: 3, color: "var(--text3)" }}>{r.exchange}</span>
                  <span style={{ fontSize: 11, color: "var(--blue)" }}>+ Add</span>
                </div>
              ))}
              {SEARCH_RESULTS.filter((r: any) => r.ticker.includes(search.toUpperCase())).length === 0 && (
                <div style={{ padding: "12px 14px", fontSize: 11, color: "var(--text3)" }}>No results for "{search}"</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Sort + type filters */}
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <span style={{ fontSize: 11, color: "var(--text3)", alignSelf: "center", marginRight: 4 }}>Sort:</span>
        {(["name", "price"] as const).map(s => (
          <button key={s} onClick={() => setSortBy(s)} style={{
            padding: "4px 12px", borderRadius: 5, border: `1px solid ${sortBy === s ? "rgba(74,158,255,0.3)" : "var(--border)"}`,
            cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 10, fontWeight: 500,
            background: sortBy === s ? "rgba(74,158,255,0.1)" : "transparent",
            color: sortBy === s ? "var(--blue)" : "var(--text3)",
          }}>{s.charAt(0).toUpperCase() + s.slice(1)}</button>
        ))}
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {isLoading && <div style={{ padding: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
        {error && <div style={{ padding: 12, color: "var(--red)", fontSize: 12 }}>Failed to load watchlist</div>}
        <table className="data-table">
          <thead>
            <tr>
              <th>Symbol</th><th>Name</th><th>Exchange</th>
              <th style={{ textAlign: "right" }}>Price</th>
              <th style={{ textAlign: "right" }}>Day High</th>
              <th style={{ textAlign: "right" }}>Day Low</th>
              <th style={{ textAlign: "right" }}>Volume</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(w => {
              const chgPct = ((w.price - (w.day_high + w.day_low) / 2) / ((w.day_high + w.day_low) / 2) * 100);
              return (
                <tr key={w.ticker} style={{ cursor: "pointer" }} onClick={() => window.location.href = "/charts"}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 13 }}>{w.ticker}</span>
                      <span style={{ fontSize: 9, padding: "1px 6px", background: "var(--bg3)", borderRadius: 3, color: "var(--text3)", textTransform: "uppercase" }}>{w.type}</span>
                    </div>
                  </td>
                  <td style={{ fontSize: 11, color: "var(--text3)" }}>{w.name}</td>
                  <td style={{ fontSize: 10 }}>{w.exchange}</td>
                  <td style={{ textAlign: "right", fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, fontSize: 13, color: "var(--text)" }}>
                    {w.price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td style={{ textAlign: "right", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--green)" }}>
                    {w.day_high > 0 ? w.day_high.toLocaleString("en-IN") : "—"}
                  </td>
                  <td style={{ textAlign: "right", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "var(--red)" }}>
                    {w.day_low > 0 ? w.day_low.toLocaleString("en-IN") : "—"}
                  </td>
                  <td style={{ textAlign: "right", fontSize: 11, color: "var(--text3)" }}>
                    {w.volume > 0 ? (w.volume / 100000).toFixed(1) + "L" : "—"}
                  </td>
                  <td>
                    <button
                      onClick={e => { e.stopPropagation(); removeSymbol(w.ticker); }}
                      style={{ fontSize: 13, color: "var(--text3)", background: "none", border: "none", cursor: "pointer", padding: "0 4px", opacity: 0.5 }}
                    >✕</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
