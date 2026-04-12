"use client";
import { useState, useEffect } from "react";

const STAR = ["","★","★★","★★★","★★★★","★★★★★"];

export default function JournalPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [stats,   setStats]   = useState<any>(null);
  const [view,    setView]    = useState<"list"|"add">("list");
  const [form,    setForm]    = useState({
    symbol:"", side:"long", entry_price:0, quantity:1,
    exit_price:"", setup:"", notes:"", tags:"", rating:3, timeframe:"15m",
  });

  const load = async () => {
    try {
      const [e, s] = await Promise.all([
        fetch("/api/v1/journal/").then(r => r.json()),
        fetch("/api/v1/journal/stats/summary").then(r => r.json()),
      ]);
      setEntries(Array.isArray(e) ? e : []);
      setStats(s);
    } catch {}
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      await fetch("/api/v1/journal/", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          ...form,
          tags: form.tags.split(",").map(t=>t.trim()).filter(Boolean),
          exit_price: form.exit_price ? parseFloat(form.exit_price as string) : undefined,
        }),
      });
      setView("list"); load();
    } catch {}
  };

  return (
    <div style={{maxWidth:960}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:20}}>
        <div>
          <h1 style={{fontFamily:"Syne,sans-serif",fontSize:20,fontWeight:700}}>Trade Journal</h1>
          <p style={{color:"var(--text3)",fontSize:11,marginTop:3}}>Record and review your trades</p>
        </div>
        <button onClick={()=>setView(view==="add"?"list":"add")}
          style={{padding:"7px 16px",background:"var(--blue)",border:"none",borderRadius:6,color:"#fff",fontFamily:"Syne,sans-serif",fontSize:12,fontWeight:600,cursor:"pointer"}}>
          {view==="add"?"← Back":"+ Log Trade"}
        </button>
      </div>

      {stats && view==="list" && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
          {[
            ["Trades",stats.total?.toString()],
            ["Total P&L",`₹${(stats.total_pnl||0).toLocaleString("en-IN")}`,stats.total_pnl>=0?"var(--green)":"var(--red)"],
            ["Win Rate",`${stats.win_rate_pct||0}%`,stats.win_rate_pct>=50?"var(--green)":"var(--red)"],
            ["Avg Win",`₹${stats.avg_win||0}`,"var(--green)"],
          ].map(([l,v,c]) => (
            <div key={l as string} style={{background:"var(--bg2)",border:"1px solid var(--border)",borderRadius:10,padding:"12px 16px"}}>
              <div style={{fontSize:10,color:"var(--text3)",fontFamily:"Syne,sans-serif",textTransform:"uppercase",letterSpacing:"1px",marginBottom:8}}>{l}</div>
              <div style={{fontFamily:"Syne,sans-serif",fontSize:20,fontWeight:700,color:(c as string)||"var(--text)"}}>{v}</div>
            </div>
          ))}
        </div>
      )}

      {view==="add" && (
        <div style={{background:"var(--bg2)",border:"1px solid var(--border)",borderRadius:10,padding:20,marginBottom:16}}>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:12}}>
            {[
              ["Symbol",    "symbol",       "text",   "RELIANCE"],
              ["Entry Price","entry_price", "number", "2800"],
              ["Quantity",  "quantity",     "number", "1"],
              ["Exit Price","exit_price",   "number", ""],
              ["Timeframe", "timeframe",    "text",   "15m"],
              ["Setup",     "setup",        "text",   "EMA crossover"],
            ].map(([label, key, type, ph]) => (
              <div key={key as string}>
                <div style={{fontSize:10,color:"var(--text3)",fontFamily:"Syne,sans-serif",textTransform:"uppercase",marginBottom:4}}>{label}</div>
                <input type={type as string} placeholder={ph as string} value={(form as any)[key as string]}
                  onChange={e=>setForm(f=>({...f,[key as string]:e.target.value}))}
                  style={{width:"100%",background:"var(--bg3)",border:"1px solid var(--border2)",borderRadius:6,padding:"7px 10px",color:"var(--text)",fontFamily:"IBM Plex Mono,monospace",fontSize:12,outline:"none"}}/>
              </div>
            ))}
          </div>
          <div style={{marginBottom:12}}>
            <div style={{fontSize:10,color:"var(--text3)",fontFamily:"Syne,sans-serif",textTransform:"uppercase",marginBottom:4}}>Notes</div>
            <textarea value={form.notes} onChange={e=>setForm(f=>({...f,notes:e.target.value}))} rows={3}
              style={{width:"100%",background:"var(--bg3)",border:"1px solid var(--border2)",borderRadius:6,padding:"7px 10px",color:"var(--text)",fontFamily:"IBM Plex Mono,monospace",fontSize:12,outline:"none",resize:"vertical"}}/>
          </div>
          <button onClick={save} style={{padding:"9px 24px",background:"var(--blue)",border:"none",borderRadius:7,color:"#fff",fontFamily:"Syne,sans-serif",fontSize:13,fontWeight:600,cursor:"pointer"}}>
            💾 Save Entry
          </button>
        </div>
      )}

      {view==="list" && (
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          {entries.length===0 && (
            <div style={{textAlign:"center",padding:48,color:"var(--text3)",fontSize:13}}>
              No entries yet. Click <strong>+ Log Trade</strong> to start.
            </div>
          )}
          {entries.map((e,i) => (
            <div key={e.id||i} style={{background:"var(--bg2)",border:"1px solid var(--border)",borderRadius:10,padding:"14px 18px"}}>
              <div style={{display:"flex",alignItems:"flex-start",gap:12}}>
                <span style={{padding:"3px 10px",borderRadius:5,fontFamily:"Syne,sans-serif",fontWeight:700,fontSize:12,flexShrink:0,background:e.side==="long"?"rgba(0,212,160,0.1)":"rgba(255,71,87,0.1)",color:e.side==="long"?"var(--green)":"var(--red)"}}>
                  {e.side?.toUpperCase()}
                </span>
                <div style={{flex:1}}>
                  <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:4}}>
                    <span style={{fontFamily:"Syne,sans-serif",fontWeight:700,fontSize:15}}>{e.symbol}</span>
                    <span style={{fontSize:10,color:"var(--text3)"}}>{e.timeframe}</span>
                    <span style={{marginLeft:"auto",fontSize:12,color:"var(--amber)"}}>{STAR[e.rating||3]}</span>
                  </div>
                  <div style={{fontSize:11,color:"var(--text3)",fontFamily:"IBM Plex Mono,monospace"}}>
                    Entry: ₹{e.entry_price} {e.exit_price?`→ Exit: ₹${e.exit_price}`:""} · Qty: {e.quantity}
                  </div>
                  {e.setup && <div style={{fontSize:12,color:"var(--text2)",marginTop:4}}>{e.setup}</div>}
                </div>
                <div style={{textAlign:"right",flexShrink:0}}>
                  {e.pnl!=null && (
                    <div style={{fontFamily:"Syne,sans-serif",fontWeight:700,fontSize:16,color:e.pnl>=0?"var(--green)":"var(--red)"}}>
                      {e.pnl>=0?"+":""}₹{e.pnl}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
