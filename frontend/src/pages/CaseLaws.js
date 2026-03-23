import { useState } from "react";
import { Card, PageTitle, Btn, Input, Tag, Ic, ICONS, ErrBox, Spinner } from "../components/UI";

const SUGGESTIONS = [
  "Bail conditions for theft under BNS",
  "Landlord tenant dispute IPC 441",
  "Domestic violence BNS 85 relief",
  "Online fraud cheating BNS 318",
  "Wrongful termination employment",
  "Dowry harassment BNS 85",
];

export default function CaseLaws({ t, toast }) {
  const [q,       setQ]       = useState("");
  const [load,    setLoad]    = useState(false);
  const [results, setResults] = useState([]);
  const [err,     setErr]     = useState(null);
  const [searched, setSearched] = useState("");

  const run = async (query) => {
    const qry = query || q;
    if (!qry.trim()) return;
    setLoad(true); setResults([]); setErr(null); setSearched(qry);
    try {
      const r = await fetch("http://localhost:8001/api/caselaws", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ query:qry }),
      });
      if (!r.ok) throw new Error((await r.json()).detail||`Error ${r.status}`);
      const d = await r.json();
      setResults(d.results||[]);
      if (!d.results?.length) toast("No results found","warning");
    } catch(e) { setErr(e.message); toast(e.message,"error"); }
    finally { setLoad(false); }
  };

  return (
    <div style={{ maxWidth:820, margin:"0 auto", padding:"52px 24px", animation:"fadeUp 0.4s ease" }}>
      <PageTitle icon="search" title="Case Law Search" badge="IndianKanoon"
        desc="Search Indian court judgments by topic. Results are pulled live from IndianKanoon and summarised in plain English by Llama-3."
        t={t} />

      {/* Search card */}
      <Card t={t} style={{ marginBottom:20 }}>
        <div style={{ display:"flex", gap:8, marginBottom:16 }}>
          <Input value={q} onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key==="Enter" && run()}
            placeholder="e.g. IPC 498A bail conditions, cheque bounce, rental eviction…"
            t={t} />
          <Btn onClick={() => run()} disabled={load||!q.trim()} loading={load} small t={t}>
            {!load && <Ic d={ICONS.search} size={14} color="#fff" sw={2} />}
          </Btn>
        </div>

        {/* Suggestion chips */}
        <div>
          <p style={{ fontSize:10, color:t.muted, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", margin:"0 0 8px" }}>
            Try these
          </p>
          <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => { setQ(s); run(s); }} style={{
                padding:"4px 12px", borderRadius:99,
                background:t.surfaceUp, border:`1.5px solid ${t.border}`,
                color:t.sub, fontSize:11, fontWeight:600, cursor:"pointer",
                fontFamily:"inherit", transition:"all 0.15s",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor=t.blue; e.currentTarget.style.color=t.blue; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor=t.border; e.currentTarget.style.color=t.sub; }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {err && <ErrBox msg={err} t={t} />}

      {/* Loading */}
      {load && (
        <div style={{ textAlign:"center", padding:"48px 0" }}>
          <Spinner c={t.blue} size={28} />
          <p style={{ color:t.sub, marginTop:16, fontSize:14, fontWeight:600 }}>Searching IndianKanoon…</p>
          <p style={{ color:t.muted, marginTop:4, fontSize:12 }}>Pulling live judgments and summarising with Llama-3</p>
        </div>
      )}

      {/* Results */}
      {!load && results.length > 0 && (
        <div>
          <p style={{ fontSize:12, color:t.muted, margin:"0 0 16px", fontWeight:600 }}>
            {results.length} result{results.length>1?"s":""} for "{searched}"
          </p>
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            {results.map((r,i) => (
              <Card t={t} key={i} style={{ animation:`fadeUp 0.3s ease ${i*0.06}s both` }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:12, marginBottom:10 }}>
                  <h4 style={{ color:t.text, fontWeight:800, fontSize:15, margin:0, lineHeight:1.4 }}>
                    {r.title||`Case ${i+1}`}
                  </h4>
                  <div style={{ display:"flex", gap:6, flexShrink:0 }}>
                    {r.year  && <Tag label={r.year}  variant="info" t={t} />}
                    {r.court && <Tag label={r.court} variant="gold" t={t} />}
                  </div>
                </div>
                <p style={{ color:t.sub, fontSize:13, lineHeight:1.8, margin:"0 0 14px" }}>
                  {r.snippet||r.summary||"No summary available."}
                </p>
                {r.url && (
                  <a href={r.url} target="_blank" rel="noreferrer"
                    style={{
                      color:t.blue, fontSize:12, fontWeight:700, textDecoration:"none",
                      display:"inline-flex", alignItems:"center", gap:5,
                      padding:"6px 14px", borderRadius:7,
                      background:`${t.blue}12`, border:`1px solid ${t.blue}22`,
                      transition:"all 0.15s",
                    }}
                    onMouseEnter={e => e.currentTarget.style.background=`${t.blue}22`}
                    onMouseLeave={e => e.currentTarget.style.background=`${t.blue}12`}
                  >
                    View full judgment <Ic d={ICONS.external} size={11} color={t.blue} sw={2} />
                  </a>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!load && results.length===0 && searched && !err && (
        <Card t={t} style={{ textAlign:"center", padding:"48px 24px" }}>
          <Ic d={ICONS.search} size={36} color={t.muted} />
          <p style={{ color:t.sub, marginTop:16, fontSize:14, fontWeight:600 }}>No results for "{searched}"</p>
          <p style={{ color:t.muted, fontSize:12, marginTop:4 }}>Try a different search term or check your API key.</p>
        </Card>
      )}
    </div>
  );
}