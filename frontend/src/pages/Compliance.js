import { useState } from "react";
import { Card, SectionTitle, PageTitle, DropZone, Btn, Textarea, Tag, Ic, ICONS, ErrBox, ProgressBar, Divider } from "../components/UI";

const SCORE_COLOR = s => s>=90?"#34d399":s>=70?"#4d7cfe":s>=50?"#fbbf24":"#f87171";
const SCORE_LABEL = s => s>=90?"Excellent":s>=70?"Good":s>=50?"Needs Work":"Critical";

export default function Compliance({ t, toast }) {
  const [mode,   setMode]   = useState("text");
  const [text,   setText]   = useState("");
  const [file,   setFile]   = useState(null);
  const [load,   setLoad]   = useState(false);
  const [result, setResult] = useState(null);
  const [err,    setErr]    = useState(null);

  const run = async () => {
    setLoad(true); setResult(null); setErr(null);
    try {
      let r;
      if (mode==="text") {
        r = await fetch("http://localhost:8001/api/compliance", {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ text }),
        });
      } else {
        const fd = new FormData(); fd.append("file", file);
        r = await fetch("http://localhost:8001/api/compliance/upload", { method:"POST", body:fd });
      }
      if (!r.ok) throw new Error((await r.json()).detail||`Error ${r.status}`);
      setResult(await r.json());
      toast("Compliance check complete ✓","success");
    } catch(e) { setErr(e.message); toast(e.message,"error"); }
    finally { setLoad(false); }
  };

  const SAMPLE = `The accused is charged under Sections 406, 420, and 506 IPC. The complainant also invokes Section 354 IPC for outrage of modesty. The FIR was registered under Section 154 CrPC and proceedings initiated under Section 156(3) CrPC. Electronic evidence has been submitted under Section 65B of the Indian Evidence Act.`;

  return (
    <div style={{ maxWidth:820, margin:"0 auto", padding:"52px 24px", animation:"fadeUp 0.4s ease" }}>
      <PageTitle icon="shield" title="BNS Compliance Checker" badge="IPC → BNS"
        desc="Detect obsolete IPC/CrPC/IEA references in any legal document. Get the correct BNS 2023 equivalents and a compliance score."
        t={t} />

      <Card t={t} style={{ marginBottom:20 }}>
        {/* Mode toggle */}
        <div style={{ display:"flex", gap:6, marginBottom:20 }}>
          {[["text","📝 Paste Text"],["pdf","📄 Upload PDF"]].map(([v,l]) => (
            <button key={v} onClick={() => setMode(v)} style={{
              padding:"7px 18px", borderRadius:9, fontSize:13, fontWeight:700,
              cursor:"pointer", fontFamily:"inherit",
              border:`1.5px solid ${mode===v ? t.blue : t.border}`,
              background: mode===v ? `${t.blue}18` : "transparent",
              color: mode===v ? t.blue : t.sub,
              transition:"all 0.15s",
            }}>{l}</button>
          ))}
        </div>

        {mode==="text"
          ? (
            <div>
              <Textarea value={text} onChange={e => setText(e.target.value)} rows={6}
                placeholder={"Paste any legal text — FIR, petition, notice, agreement…"} t={t} />
              <button onClick={() => setText(SAMPLE)} style={{
                marginTop:8, background:"none", border:"none",
                color:t.blue, fontSize:11, fontWeight:700, cursor:"pointer",
                fontFamily:"inherit", letterSpacing:"0.03em",
              }}>
                Try sample text →
              </button>
            </div>
          )
          : <DropZone onFile={setFile} accept=".pdf" hint="PDF documents only · Max 10 MB" t={t} />
        }

        <div style={{ marginTop:18, display:"flex", gap:10, alignItems:"center" }}>
          <Btn onClick={run}
            disabled={load || (mode==="text" ? !text.trim() : !file)}
            loading={load} t={t}>
            {load ? "Checking…" : "Check Compliance"}
          </Btn>
          {result && (
            <button onClick={() => { setResult(null); setText(""); setFile(null); }} style={{
              background:"none", border:"none", cursor:"pointer",
              color:t.sub, fontSize:13, fontFamily:"inherit", fontWeight:600,
            }}>Clear</button>
          )}
        </div>
      </Card>

      {err && <ErrBox msg={err} t={t} />}

      {result && (
        <div style={{ animation:"fadeUp 0.3s ease" }}>
          {/* Score card */}
          <Card t={t} style={{ marginBottom:16 }}>
            <div style={{ display:"flex", gap:28, alignItems:"center", marginBottom:20, flexWrap:"wrap" }}>
              {/* Circular progress */}
              <div style={{ position:"relative", width:100, height:100, flexShrink:0 }}>
                <svg width="100" height="100" style={{ transform:"rotate(-90deg)" }}>
                  <circle cx="50" cy="50" r="42" fill="none" stroke={t.border} strokeWidth="8"/>
                  <circle cx="50" cy="50" r="42" fill="none"
                    stroke={SCORE_COLOR(result.score)} strokeWidth="8"
                    strokeDasharray={`${2*Math.PI*42}`}
                    strokeDashoffset={`${2*Math.PI*42*(1-result.score/100)}`}
                    strokeLinecap="round"
                    style={{ transition:"stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1)" }}
                  />
                </svg>
                <div style={{
                  position:"absolute", inset:0,
                  display:"flex", flexDirection:"column",
                  alignItems:"center", justifyContent:"center",
                }}>
                  <span style={{ fontSize:22, fontWeight:900, color:SCORE_COLOR(result.score), lineHeight:1 }}>
                    {result.score}
                  </span>
                  <span style={{ fontSize:10, color:t.muted, fontWeight:700 }}>/ 100</span>
                </div>
              </div>

              <div style={{ flex:1 }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
                  <span style={{ fontSize:20, fontWeight:900, color:SCORE_COLOR(result.score), letterSpacing:"-0.02em" }}>
                    {SCORE_LABEL(result.score)}
                  </span>
                  {result.grade && (
                    <Tag label={`Grade ${result.grade}`}
                      variant={result.grade==="A"?"success":result.grade==="B"?"info":"warning"}
                      t={t} />
                  )}
                </div>
                <p style={{ fontSize:14, color:t.sub, margin:0, lineHeight:1.7 }}>{result.note}</p>
                {result.score < 70 && (
                  <div style={{
                    marginTop:12, padding:"8px 14px", borderRadius:8,
                    background:t.amberDim, border:`1px solid ${t.amber}33`,
                    fontSize:12, color:t.amber, fontWeight:600,
                    display:"flex", gap:8, alignItems:"center",
                  }}>
                    <Ic d={ICONS.alert} size={13} color={t.amber} />
                    Update all IPC/CrPC references before filing — courts may reject on technical grounds.
                  </div>
                )}
              </div>
            </div>

            {/* Mappings */}
            {result.mappings?.length > 0 && (
              <>
                <Divider t={t} label={`${result.mappings.length} correction${result.mappings.length>1?"s":""} found`} />
                <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                  {result.mappings.map((m,i) => (
                    <div key={i} style={{
                      display:"flex", gap:12, alignItems:"center", flexWrap:"wrap",
                      padding:"11px 16px", borderRadius:10,
                      background: m.new==="ABOLISHED" ? "#450a0a" : "#052e1c",
                      border:`1px solid ${m.new==="ABOLISHED" ? "#f8717133" : "#34d39933"}`,
                      animation:`fadeUp 0.2s ease ${i*0.04}s both`,
                      transition:"transform 0.15s",
                    }}
                      onMouseEnter={e => e.currentTarget.style.transform="translateX(3px)"}
                      onMouseLeave={e => e.currentTarget.style.transform="translateX(0)"}
                    >
                      <code style={{
                        padding:"3px 10px", borderRadius:6,
                        background:"#f8717122", border:"1px solid #f8717144",
                        fontSize:13, fontWeight:700, color:"#f87171",
                        flexShrink:0,
                      }}>{m.old}</code>
                      <Ic d={ICONS.arrow} size={13} color={t.muted} />
                      <code style={{
                        padding:"3px 10px", borderRadius:6,
                        background: m.new==="ABOLISHED" ? "#f8717122" : "#34d39922",
                        border:`1px solid ${m.new==="ABOLISHED" ? "#f8717144" : "#34d39944"}`,
                        fontSize:13, fontWeight:700,
                        color: m.new==="ABOLISHED" ? "#f87171" : "#34d399",
                        flexShrink:0,
                      }}>{m.new}</code>
                      <span style={{ fontSize:12, color:t.sub, flex:1 }}>{m.name}</span>
                      {m.new==="ABOLISHED" && (
                        <span style={{
                          fontSize:9, fontWeight:800, color:"#f87171",
                          padding:"2px 7px", borderRadius:4,
                          background:"#f8717122", letterSpacing:"0.06em", textTransform:"uppercase",
                        }}>Abolished</span>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}