"use client";
import { useState, useEffect, useCallback } from "react";

const SIG: Record<string,{color:string,bg:string,icon:string}> = {
  BUY:  {color:"var(--green)", bg:"rgba(0,212,160,0.1)",  icon:"▲"},
  SELL: {color:"var(--red)",   bg:"rgba(255,71,87,0.1)",  icon:"▼"},
  HOLD: {color:"var(--amber)", bg:"rgba(255,179,71,0.08)",icon:"◆"},
};

export default function ScreenerPage() {
  const [results, setResults]   = useState<any[]>([]);
  const [loading, setLoading]   = useState(false);
  const [tf,      setTf]        = useState("15m");
  const [sigF,    setSigF]      = useState("ALL");
  const [aiOnline,setAiOnline]  = useState<boolean|null>(null);
  const [lastScan,setLastScan]  = useState<string|null>(null);

  const scan = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/screener/scan?timeframe=${tf}&limit=14`);
      const data: any[] = await r.json();
      setResults(data);
      setLastScan(new Date().toLocaleTimeString());
      setAiOnline(data.some((d:any)=>d.available));
    } catch { setResults([]); }
    finally { setLoading(false); }
  }, [tf]);

  useEffect(() => { scan(); }, [scan]);

  const filtered = sigF==="ALL" ? results : results.filter(r=>r.signal===sigF);
  const buys = results.filter(r=>r.signal==="BUY").length;
  const sells = results.filter(r=>r.signal==="SELL").length;

  return (
    <div style={{maxWidth:1100}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:20}}>
        <div>
          <h1 style={{fontFamily:"Syne,sans-serif",fontSize:20,fontWeight:700}}>Screener</h1>
          <p style={{color:"var(--text3)",fontSize:11,marginTop:3}}>
            AI signal scanner · {lastScan&&`Last: ${lastScan}`}
          </p>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          {aiOnline!==null&&(
            <div style={{padding:"4px 10px",borderRadius:5,fontSize:10,fontFamily:"Syne,sans-serif",fontWeight:500,
              background:aiOnline?"rgba(0,212,160,0.08)":"rgba(255,179,71,0.08)",
              color:aiOnline?"var(--green)":"var(--amber)",
              border:`1px solid ${aiOnline?"rgba(0,212,160,0.25)":"rgba(255,179,71,0.25)"}`}}>
              {aiOnline?"● AI Online":"● Technical Only"}
            </div>
          )}
          <button onClick={scan} disabled={loading}
            style={{padding:"7px 18px",background:"var(--blue)",border:"none",borderRadius:6,color:"#fff",fontFamily:"Syne,sans-serif",fontSize:12,fontWeight:600,cursor:"pointer",opacity:loading?0.7:1}}>
            {loading?"Scanning…":"▶ Scan"}
          </button>
        </div>
      </div>

      <div style={{display:"flex",gap:8,marginBottom:14,flexWrap:"wrap"}}>
        {["1m","5m","15m","30m","1h","4h","1d"].map(t=>(
          <button key={t} onClick={()=>setTf(t)}
            style={{padding:"4px 12px",borderRadius:5,border:"none",cursor:"pointer",fontFamily:"IBM Plex Mono,monospace",fontSize:11,background:tf===t?"var(--bg1)":"var(--bg3)",color:tf===t?"var(--text)":"var(--text3)"}}>
            {t}
          </button>
        ))}
        <div style={{flex:1}}/>
        {["ALL","BUY","SELL","HOLD"].map(s=>(
          <button key={s} onClick={()=>setSigF(s)}
            style={{padding:"4px 12px",borderRadius:5,border:"none",cursor:"pointer",fontFamily:"Syne,sans-serif",fontSize:11,fontWeight:500,background:sigF===s?"var(--bg1)":"var(--bg3)",color:sigF===s?"var(--text)":"var(--text3)"}}>
            {s}
          </button>
        ))}
      </div>

      <div style={{display:"flex",gap:10,marginBottom:14}}>
        {[
          [`${buys} BUY`,"var(--green)","rgba(0,212,160,0.1)"],
          [`${sells} SELL`,"var(--red)","rgba(255,71,87,0.1)"],
          [`${results.length-buys-sells} HOLD`,"var(--amber)","rgba(255,179,71,0.08)"],
        ].map(([label,color,bg])=>(
          <div key={label as string} style={{padding:"4px 12px",borderRadius:5,background:bg as string,color:color as string,fontFamily:"Syne,sans-serif",fontSize:12,fontWeight:600}}>
            {label}
          </div>
        ))}
      </div>

      <div style={{background:"var(--bg2)",border:"1px solid var(--border)",borderRadius:10,overflow:"hidden"}}>
        <table style={{width:"100%",borderCollapse:"collapse"}}>
          <thead>
            <tr>
              {["Symbol","Exchange","Signal","Confidence","XGBoost","AI"].map(h=>(
                <th key={h} style={{fontSize:10,color:"var(--text3)",fontFamily:"Syne,sans-serif",fontWeight:500,textTransform:"uppercase",letterSpacing:"1px",padding:"8px 12px",textAlign:"left",borderBottom:"1px solid var(--border)"}}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && !filtered.length ? (
              <tr><td colSpan={6} style={{padding:32,textAlign:"center",color:"var(--text3)"}}>Scanning…</td></tr>
            ) : filtered.map((r,i)=>{
              const cfg=SIG[r.signal]||SIG.HOLD;
              return (
                <tr key={r.symbol+i}>
                  <td style={{padding:"10px 12px",fontFamily:"Syne,sans-serif",fontWeight:700,fontSize:13}}>{r.symbol}</td>
                  <td style={{padding:"10px 12px",fontSize:11,color:"var(--text3)"}}>{r.exchange}</td>
                  <td style={{padding:"10px 12px"}}>
                    <span style={{padding:"3px 10px",borderRadius:5,fontFamily:"Syne,sans-serif",fontWeight:700,fontSize:12,background:cfg.bg,color:cfg.color}}>
                      {cfg.icon} {r.signal}
                    </span>
                  </td>
                  <td style={{padding:"10px 12px"}}>
                    <div style={{display:"flex",alignItems:"center",gap:8}}>
                      <div style={{width:60,height:4,background:"var(--bg3)",borderRadius:2,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${(r.confidence||0)*100}%`,background:cfg.color,borderRadius:2}}/>
                      </div>
                      <span style={{fontSize:11,fontFamily:"IBM Plex Mono,monospace",color:cfg.color}}>
                        {((r.confidence||0)*100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td style={{padding:"10px 12px",fontSize:11,color:r.xgb_signal==="UP"?"var(--green)":r.xgb_signal==="DOWN"?"var(--red)":"var(--text3)"}}>
                    {r.xgb_signal||"—"}
                  </td>
                  <td style={{padding:"10px 12px"}}>
                    <span style={{fontSize:9,padding:"2px 6px",borderRadius:3,background:r.available?"rgba(0,212,160,0.1)":"var(--bg3)",color:r.available?"var(--green)":"var(--text3)"}}>
                      {r.available?"ML":"Tech"}
                    </span>
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
