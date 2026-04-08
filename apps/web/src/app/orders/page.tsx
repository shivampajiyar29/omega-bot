"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOrders } from "@/hooks/useApi";
import { cancelOrder } from "@/lib/api";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  filled:    { background: "rgba(0,212,160,0.1)",  color: "var(--green)", borderColor: "rgba(0,212,160,0.2)" },
  open:      { background: "rgba(74,158,255,0.1)", color: "var(--blue)",  borderColor: "rgba(74,158,255,0.2)" },
  cancelled: { background: "rgba(255,255,255,0.05)", color: "var(--text3)", borderColor: "var(--border)" },
  rejected:  { background: "rgba(255,71,87,0.1)",  color: "var(--red)",   borderColor: "rgba(255,71,87,0.2)" },
  pending:   { background: "rgba(255,179,71,0.1)", color: "var(--amber)", borderColor: "rgba(255,179,71,0.2)" },
};

export default function OrdersPage() {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const params = { status: filter === "all" ? undefined : filter, symbol: search || undefined, limit: 200 };
  const { data: orders = [], isLoading, error, refetch } = useOrders(params);
  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelOrder(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orders"] }),
  });

  const filtered = orders;

  return (
    <div style={{ maxWidth: 1100 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700 }}>Orders</h1>
          <p style={{ color: "var(--text3)", fontSize: 11, marginTop: 3 }}>All placed orders — paper and live.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="Search symbol…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ background: "var(--bg3)", border: "1px solid var(--border2)", borderRadius: 6, padding: "6px 12px", color: "var(--text)", fontFamily: "IBM Plex Mono, monospace", fontSize: 12, outline: "none", width: 160 }}
          />
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 14 }}>
        {["all", "open", "filled", "cancelled"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "5px 14px", borderRadius: 5, border: "1px solid var(--border)",
              cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 500,
              background: filter === f ? "var(--bg3)" : "transparent",
              color: filter === f ? "var(--text)" : "var(--text3)",
            }}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== "all" && <span style={{ marginLeft: 6, fontSize: 10, color: "var(--text3)" }}>
              ({orders.filter((o: any) => o.status === f).length})
            </span>}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: "var(--text3)", alignSelf: "center" }}>
          {filtered.length} order{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {isLoading && <div style={{ padding: 12, color: "var(--text3)", fontSize: 12 }}>Loading...</div>}
        {error && (
          <div style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <div style={{ color: "var(--red)", fontSize: 12 }}>Failed to load orders (backend may be down)</div>
            <button
              onClick={() => refetch()}
              style={{ padding: "6px 10px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text2)", cursor: "pointer", fontFamily: "Syne, sans-serif", fontSize: 11, fontWeight: 600 }}
            >
              Retry
            </button>
          </div>
        )}
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th><th>Symbol</th><th>Side</th><th>Type</th>
                <th>Qty</th><th>Price</th><th>Filled</th><th>Avg Fill</th>
                <th>Status</th><th>Mode</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((o: any) => (
                <tr key={o.id}>
                  <td style={{ color: "var(--text3)", fontFamily: "IBM Plex Mono, monospace" }}>{o.placed_at ? new Date(o.placed_at).toLocaleTimeString("en-IN", { hour12: false }) : "--:--:--"}</td>
                  <td style={{ fontFamily: "Syne, sans-serif", fontWeight: 600, color: "var(--text)" }}>
                    {o.symbol}
                    <span style={{ fontSize: 10, color: "var(--text3)", fontWeight: 400, marginLeft: 4 }}>{o.exchange}</span>
                  </td>
                  <td>
                    <span style={{
                      fontSize: 11, fontFamily: "Syne, sans-serif", fontWeight: 600, padding: "2px 8px", borderRadius: 4,
                      background: o.side === "buy" ? "rgba(0,212,160,0.1)" : "rgba(255,71,87,0.1)",
                      color: o.side === "buy" ? "var(--green)" : "var(--red)",
                    }}>
                      {o.side.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ textTransform: "capitalize" }}>{o.order_type}</td>
                  <td>{o.quantity}</td>
                  <td>{o.price ? `₹${o.price.toLocaleString()}` : <span style={{ color: "var(--text3)" }}>MKT</span>}</td>
                  <td>{o.filled_quantity}</td>
                  <td>{o.avg_fill_price ? `₹${Number(o.avg_fill_price).toLocaleString()}` : <span style={{ color: "var(--text3)" }}>—</span>}</td>
                  <td>
                    <span style={{
                      fontSize: 10, padding: "2px 8px", borderRadius: 4,
                      fontFamily: "Syne, sans-serif", fontWeight: 500,
                      border: "1px solid",
                      ...STATUS_STYLE[o.status] ?? STATUS_STYLE.pending,
                    }}>
                      {o.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: 10, padding: "2px 7px", background: "var(--bg3)", borderRadius: 4, color: "var(--text3)" }}>
                      {String(o.trading_mode ?? "paper").toUpperCase()}
                    </span>
                  </td>
                  <td>
                    {o.status === "open" && (
                      <button
                        onClick={() => cancelMutation.mutate(o.id)}
                        style={{ fontSize: 10, padding: "3px 10px", background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.2)", borderRadius: 4, color: "var(--red)", cursor: "pointer", fontFamily: "Syne, sans-serif" }}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && !error && filtered.length === 0 && (
                <tr>
                  <td colSpan={11} style={{ padding: 26, textAlign: "center", color: "var(--text3)", fontSize: 12 }}>
                    No orders yet. Place a paper trade to see it here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
