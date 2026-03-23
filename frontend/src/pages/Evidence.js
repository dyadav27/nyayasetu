import { useState } from "react";
import { Card, SectionTitle, PageTitle, DropZone, Btn, Input, Textarea, Tag, Ic, ICONS, ErrBox } from "../components/UI";

export default function Evidence({ t, toast }) {
  const [file,   setFile]   = useState(null);
  const [prev,   setPrev]   = useState(null);
  const [name,   setName]   = useState("");
  const [brief,  setBrief]  = useState("");
  const [load,   setLoad]   = useState(false);
  const [cert,   setCert]   = useState(null);
  const [err,    setErr]    = useState(null);

  const pickFile = (f) => {
    setFile(f); setCert(null); setErr(null);
    const rd = new FileReader();
    rd.onload = e => setPrev(e.target.result);
    rd.readAsDataURL(f);
  };

  const run = async () => {
    setLoad(true); setCert(null); setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("complainant_name", name || "Unknown");
      fd.append("incident_brief",   brief || "Evidence submitted via NyayaSetu");
      const r = await fetch("http://localhost:8001/api/evidence", { method:"POST", body:fd });
      if (!r.ok) throw new Error((await r.json()).detail||`Error ${r.status}`);
      setCert(await r.json());
      toast("Certificate generated ✓","success");
    } catch(e) { setErr(e.message); toast(e.message,"error"); }
    finally { setLoad(false); }
  };

  const FIELDS = cert ? [
    { label:"Certificate ID",   value:`NS-${cert.certificate_id}`,   mono:true  },
    { label:"File Name",        value:cert.file_name                             },
    { label:"File Size",        value:`${Math.round((cert.file_size_bytes||0)/1024)} KB` },
    { label:"Device",           value:`${cert.device_make} ${cert.device_model}`.trim() || "Not recorded" },
    { label:"GPS",              value:cert.gps_coordinates || "Not available"   },
    { label:"Captured",         value:cert.capture_timestamp || "—"             },
    { label:"Legal Basis",      value:cert.bsa_section || "BSA Section 63"      },
    { label:"Integrity",        value:cert.verification_status,       color:"#34d399" },
  ] : [];

  return (
    <div style={{ maxWidth:800, margin:"0 auto", padding:"52px 24px", animation:"fadeUp 0.4s ease" }}>
      <PageTitle icon="camera" title="Evidence Certificate" badge="BSA §63"
        desc="Generate a SHA-256 cryptographic certificate for digital evidence. Hash is computed before any processing — preserving chain of custody."
        t={t} />

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }} className="ev-grid">
        {/* Left: Upload + form */}
        <Card t={t}>
          <SectionTitle t={t}>Upload Evidence Photo</SectionTitle>

          {/* Preview or dropzone */}
          {prev ? (
            <div style={{
              borderRadius:10, overflow:"hidden", marginBottom:16,
              border:`1.5px solid ${t.border}`, position:"relative",
            }}>
              <img src={prev} alt="preview" style={{ width:"100%", maxHeight:200, objectFit:"cover", display:"block" }} />
              <button onClick={() => { setFile(null); setPrev(null); setCert(null); }} style={{
                position:"absolute", top:8, right:8,
                background:"rgba(0,0,0,0.7)", border:"none", borderRadius:6,
                color:"#fff", cursor:"pointer", padding:"4px 8px", fontSize:11, fontWeight:700,
                fontFamily:"inherit",
              }}>
                Change
              </button>
            </div>
          ) : (
            <div style={{ marginBottom:16 }}>
              <DropZone onFile={pickFile} accept=".jpg,.jpeg,.png,.webp"
                hint="JPG, PNG, WebP · Any size" t={t} />
            </div>
          )}

          {/* Optional fields */}
          <div style={{ marginBottom:10 }}>
            <label style={{ fontSize:11, color:t.sub, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.07em", display:"block", marginBottom:6 }}>
              Your Name (optional)
            </label>
            <Input value={name} onChange={e => setName(e.target.value)}
              placeholder="Full name of complainant" t={t} />
          </div>

          <div style={{ marginBottom:18 }}>
            <label style={{ fontSize:11, color:t.sub, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.07em", display:"block", marginBottom:6 }}>
              Incident Description (optional)
            </label>
            <Textarea value={brief} onChange={e => setBrief(e.target.value)} rows={3}
              placeholder="e.g. Phone snatched near Andheri station, 22 March 2026" t={t} />
          </div>

          <Btn onClick={run} disabled={load||!file} loading={load} t={t} style={{ width:"100%" }}>
            <Ic d={ICONS.shield} size={15} color="#fff" sw={2} />
            {load ? "Computing SHA-256…" : "Generate Certificate"}
          </Btn>
          {err && <ErrBox msg={err} t={t} />}
        </Card>

        {/* Right: Certificate output */}
        <Card t={t}>
          <SectionTitle t={t}>Certificate Details</SectionTitle>

          {!cert && !load && (
            <div style={{ textAlign:"center", padding:"48px 20px", color:t.muted }}>
              <div style={{
                width:64, height:64, borderRadius:16,
                background:`${t.blue}12`, border:`1px solid ${t.blue}22`,
                display:"flex", alignItems:"center", justifyContent:"center",
                margin:"0 auto 16px",
              }}>
                <Ic d={ICONS.shield} size={28} color={t.muted} />
              </div>
              <p style={{ fontSize:13 }}>Upload a photo and click Generate</p>
            </div>
          )}

          {load && (
            <div style={{ textAlign:"center", padding:"48px 20px" }}>
              <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}>
                <svg width="56" height="56" viewBox="0 0 56 56">
                  <circle cx="28" cy="28" r="22" fill="none" stroke={t.border} strokeWidth="4"/>
                  <circle cx="28" cy="28" r="22" fill="none" stroke={t.blue} strokeWidth="4"
                    strokeDasharray="138" strokeDashoffset="100" strokeLinecap="round"
                    style={{ animation:"spin 1s linear infinite", transformOrigin:"center" }}/>
                </svg>
              </div>
              <p style={{ color:t.sub, fontSize:13, fontWeight:600 }}>Computing SHA-256 hash…</p>
              <p style={{ color:t.muted, fontSize:11, marginTop:4 }}>Chain of custody preserved</p>
            </div>
          )}

          {cert && (
            <div style={{ animation:"fadeUp 0.3s ease" }}>
              {/* Verified badge */}
              <div style={{
                padding:"10px 14px", borderRadius:9, marginBottom:18,
                background:"#052e1c", border:"1px solid #34d39933",
                display:"flex", alignItems:"center", gap:8,
              }}>
                <div style={{
                  width:24, height:24, borderRadius:6,
                  background:"#34d39922", display:"flex", alignItems:"center", justifyContent:"center",
                }}>
                  <Ic d={ICONS.check} size={12} color="#34d399" sw={2.5} />
                </div>
                <span style={{ fontSize:13, color:"#34d399", fontWeight:700 }}>
                  {cert.verification_status || "INTEGRITY VERIFIED"}
                </span>
              </div>

              {/* SHA-256 */}
              <div style={{
                padding:"12px 14px", borderRadius:9, marginBottom:16,
                background:t.bg, border:`1.5px solid ${t.border}`,
              }}>
                <p style={{ fontSize:10, color:t.muted, fontWeight:800, textTransform:"uppercase", letterSpacing:"0.07em", margin:"0 0 6px" }}>
                  SHA-256 Hash
                </p>
                <p style={{
                  fontFamily:"monospace", fontSize:11, color:t.text,
                  wordBreak:"break-all", margin:0, lineHeight:1.7,
                }}>
                  {cert.sha256_hash}
                </p>
              </div>

              {/* Fields grid */}
              <div style={{ display:"flex", flexDirection:"column", gap:6, marginBottom:16 }}>
                {FIELDS.filter(f => f.label !== "Integrity").map((f,i) => (
                  <div key={i} style={{
                    display:"flex", gap:10, padding:"8px 12px",
                    borderRadius:7, background:t.surfaceUp,
                    border:`1px solid ${t.border}`,
                    fontSize:12,
                  }}>
                    <span style={{ color:t.muted, minWidth:90, fontWeight:600, flexShrink:0 }}>{f.label}</span>
                    <span style={{
                      color:f.color||t.text, fontFamily:f.mono?"monospace":"inherit",
                      wordBreak:"break-all", fontWeight:f.color?700:400,
                    }}>{f.value}</span>
                  </div>
                ))}
              </div>

              {/* Download button */}
              {cert.pdf_download_url && (
                <a href={`http://localhost:8001${cert.pdf_download_url}`} target="_blank" rel="noreferrer"
                  style={{ textDecoration:"none", display:"block" }}>
                  <Btn t={t} onClick={() => {}}>
                    <Ic d={ICONS.download} size={14} color="#fff" sw={2} />
                    Download Certificate PDF
                  </Btn>
                </a>
              )}

              <div style={{
                marginTop:12, padding:"8px 12px", borderRadius:7,
                background:t.surfaceUp, border:`1px solid ${t.border}`,
                fontSize:11, color:t.muted, lineHeight:1.7,
              }}>
                Verify: <code>sha256sum &lt;file&gt;</code> (Linux/Mac) ·{" "}
                <code>certutil -hashfile &lt;file&gt; SHA256</code> (Windows)
              </div>
            </div>
          )}
        </Card>
      </div>

      <style>{`
        @media (max-width:640px) { .ev-grid{grid-template-columns:1fr!important;} }
      `}</style>
    </div>
  );
}