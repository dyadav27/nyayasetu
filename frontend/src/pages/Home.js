import { useState, useEffect } from "react";
import { Ic, ICONS, Tag, AnimNum, Divider } from "../components/UI";

const STATS = [
  { value:"3,254", label:"Legal chunks indexed", icon:"doc",    color:"#4d7cfe" },
  { value:"70+",   label:"IPC → BNS mappings",  icon:"shield", color:"#34d399" },
  { value:"18",    label:"BNS offences covered", icon:"scale",  color:"#fbbf24" },
  { value:"100%",  label:"BSA §63 compliant",    icon:"camera", color:"#a78bfa" },
];

const FEATURES = [
  {
    id:"analyzer",   icon:"doc",
    title:"Document Analyzer",
    color:"#4d7cfe",
    desc:"Upload a rental agreement, employment contract, FIR, or legal notice. Get every clause scored Safe, Caution, High Risk, or Illegal — with plain-language explanation.",
    tags:["Risk Scoring","Q&A","Case Laws"],
    stat:"15 clause types",
  },
  {
    id:"compliance", icon:"shield",
    title:"BNS Compliance",
    color:"#34d399",
    desc:"Paste any legal text or upload a PDF. Detects every obsolete IPC/CrPC/IEA reference and shows the correct BNS 2023 / BNSS 2023 / BSA 2023 equivalent.",
    tags:["IPC → BNS","Score 0–100","Auto-map"],
    stat:"70+ mappings",
  },
  {
    id:"evidence",   icon:"camera",
    title:"Evidence Certificate",
    color:"#fbbf24",
    desc:"Upload a photo as evidence. SHA-256 hash computed before any processing — preserving chain of custody. Certificate is admissible under BSA Section 63.",
    tags:["SHA-256","BSA §63","PDF Export"],
    stat:"Chain of custody",
  },
  {
    id:"caselaws",   icon:"search",
    title:"Case Law Search",
    color:"#a78bfa",
    desc:"Search Indian court judgments by topic. Pulled live from IndianKanoon and summarised in plain English by Llama-3 running on your local GPU.",
    tags:["IndianKanoon","Llama-3","Live"],
    stat:"Live API",
  },
];

const DOT_GRID = Array.from({ length: 120 });

export default function Home({ t, go }) {
  const [hov, setHov] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(id);
  }, []);

  return (
    <div style={{ maxWidth:1060, margin:"0 auto", padding:"60px 24px 80px" }}>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <div style={{
        position:"relative", marginBottom:72, overflow:"hidden",
        borderRadius:20, padding:"64px 52px 56px",
        background:`linear-gradient(135deg, ${t.surface} 0%, ${t.surfaceUp} 100%)`,
        border:`1.5px solid ${t.border}`,
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(20px)",
        transition:"opacity 0.5s ease, transform 0.5s ease",
      }}>
        {/* Dot grid background */}
        <div style={{ position:"absolute", inset:0, overflow:"hidden", borderRadius:20, opacity:0.04 }}>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(20,1fr)", gap:16, padding:24 }}>
            {DOT_GRID.map((_,i) => (
              <div key={i} style={{ width:3, height:3, borderRadius:"50%", background:t.blue }} />
            ))}
          </div>
        </div>

        {/* Glow orb */}
        <div style={{
          position:"absolute", top:-80, right:-80, width:360, height:360,
          borderRadius:"50%", background:`radial-gradient(circle, ${t.blue}18 0%, transparent 70%)`,
          pointerEvents:"none",
        }}/>

        <div style={{ position:"relative" }}>
          {/* Eyebrow */}
          <div style={{
            display:"inline-flex", alignItems:"center", gap:8,
            padding:"5px 14px", borderRadius:99,
            background:`${t.blue}15`, border:`1px solid ${t.blue}33`,
            marginBottom:24,
          }}>
            <Ic d={ICONS.scale} size={12} color={t.blue} sw={2.5} />
            <span style={{ fontSize:11, color:t.blue, fontWeight:800, letterSpacing:"0.08em", textTransform:"uppercase" }}>
              Indian Legal AI · BNS 2023
            </span>
          </div>

          {/* Headline — uses serif font for gravitas */}
          <h1 style={{
            fontFamily:"'DM Serif Display', Georgia, serif",
            fontSize:"clamp(2.4rem, 5vw, 3.8rem)",
            fontWeight:400, color:t.text, lineHeight:1.1,
            margin:"0 0 20px", letterSpacing:"-0.01em",
          }}>
            Legal clarity,<br />
            <span style={{ color: t.blue }}>
  without a lawyer.
</span>
          </h1>

          <p style={{ fontSize:16, color:t.sub, maxWidth:500, lineHeight:1.8, margin:"0 0 36px" }}>
            Understand legal documents, check BNS compliance, certify evidence,
            and search Indian case law — running locally on your machine.
          </p>

          <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
            <button onClick={() => go("analyzer")} style={{
              padding:"12px 26px", borderRadius:10,
              background:t.blue, color:"#fff",
              border:"none", fontSize:14, fontWeight:700,
              cursor:"pointer", display:"flex", alignItems:"center", gap:8,
              fontFamily:"inherit", transition:"all 0.2s",
              boxShadow:`0 4px 20px ${t.blue}55`,
            }}
              onMouseEnter={e => { e.currentTarget.style.transform="translateY(-2px)"; e.currentTarget.style.boxShadow=`0 8px 28px ${t.blue}66`; }}
              onMouseLeave={e => { e.currentTarget.style.transform="translateY(0)"; e.currentTarget.style.boxShadow=`0 4px 20px ${t.blue}55`; }}
            >
              <Ic d={ICONS.doc} size={15} color="#fff" sw={2} />
              Analyze a Document
            </button>
            <button onClick={() => go("compliance")} style={{
              padding:"12px 24px", borderRadius:10,
              background:"transparent", color:t.text,
              border:`1.5px solid ${t.border}`, fontSize:14, fontWeight:600,
              cursor:"pointer", display:"flex", alignItems:"center", gap:8,
              fontFamily:"inherit", transition:"all 0.2s",
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor=t.borderHover; e.currentTarget.style.transform="translateY(-2px)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor=t.border; e.currentTarget.style.transform="translateY(0)"; }}
            >
              <Ic d={ICONS.shield} size={14} color={t.sub} />
              Check BNS Compliance
            </button>
          </div>
        </div>
      </div>

      {/* ── Stats ────────────────────────────────────────────── */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:64 }} className="stat-grid">
        {STATS.map((s, i) => (
          <div key={i} style={{
            background:t.surface, border:`1.5px solid ${t.border}`,
            borderRadius:14, padding:"20px 18px",
            opacity: visible ? 1 : 0,
            transform: visible ? "translateY(0)" : "translateY(16px)",
            transition:`opacity 0.4s ease ${0.1+i*0.08}s, transform 0.4s ease ${0.1+i*0.08}s, border-color 0.2s`,
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor=s.color+"55"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor=t.border; }}
          >
            <div style={{
              width:34, height:34, borderRadius:9,
              background:`${s.color}18`, border:`1px solid ${s.color}33`,
              display:"flex", alignItems:"center", justifyContent:"center", marginBottom:12,
            }}>
              <Ic d={ICONS[s.icon]} size={15} color={s.color} />
            </div>
            <div style={{ fontSize:"1.8rem", fontWeight:900, color:t.text, margin:"0 0 3px", letterSpacing:"-0.03em", lineHeight:1 }}>
              <AnimNum target={s.value} />
            </div>
            <div style={{ fontSize:11, color:t.sub, fontWeight:500 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Feature Cards ─────────────────────────────────────── */}
      <Divider t={t} label="What you can do" />

      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))", gap:16, marginBottom:52 }}>
        {FEATURES.map((f, i) => (
          <button key={f.id} onClick={() => go(f.id)}
            onMouseEnter={() => setHov(f.id)}
            onMouseLeave={() => setHov(null)}
            style={{
              background:t.surface,
              border:`1.5px solid ${hov===f.id ? f.color+"55" : t.border}`,
              borderRadius:16, padding:"24px 22px",
              textAlign:"left", cursor:"pointer",
              transition:"all 0.22s cubic-bezier(0.34,1.56,0.64,1)",
              transform: hov===f.id ? "translateY(-4px) scale(1.01)" : "translateY(0) scale(1)",
              boxShadow: hov===f.id ? `0 16px 40px ${f.color}22` : "none",
              opacity: visible ? 1 : 0,
              animationDelay:`${0.3+i*0.08}s`,
            }}
          >
            {/* Icon with animated glow */}
            <div style={{
              width:46, height:46, borderRadius:13,
              background:`${f.color}18`, border:`1px solid ${f.color}33`,
              display:"flex", alignItems:"center", justifyContent:"center",
              marginBottom:18,
              transform: hov===f.id ? "scale(1.1) rotate(-3deg)" : "scale(1) rotate(0deg)",
              transition:"transform 0.25s ease",
              boxShadow: hov===f.id ? `0 4px 16px ${f.color}44` : "none",
            }}>
              <Ic d={ICONS[f.icon]} size={20} color={f.color} />
            </div>

            <div style={{ fontSize:15, fontWeight:800, color:t.text, marginBottom:8, letterSpacing:"-0.01em" }}>{f.title}</div>
            <p style={{ fontSize:13, color:t.sub, lineHeight:1.7, margin:"0 0 16px" }}>{f.desc}</p>

            {/* Tags */}
            <div style={{ display:"flex", gap:5, flexWrap:"wrap", marginBottom:18 }}>
              {f.tags.map(tag => (
                <span key={tag} style={{
                  padding:"2px 8px", borderRadius:6,
                  background:`${f.color}14`, color:f.color,
                  fontSize:10, fontWeight:700, letterSpacing:"0.03em",
                  border:`1px solid ${f.color}22`,
                }}>{tag}</span>
              ))}
            </div>

            {/* Arrow CTA */}
            <div style={{
              display:"flex", alignItems:"center", gap:6,
              fontSize:12, color:f.color, fontWeight:700, letterSpacing:"0.02em",
              opacity: hov===f.id ? 1 : 0.6, transition:"all 0.2s",
              transform: hov===f.id ? "translateX(4px)" : "translateX(0)",
            }}>
              Open tool
              <Ic d={ICONS.arrow} size={12} color={f.color} sw={2.5} />
            </div>
          </button>
        ))}
      </div>

      {/* ── Tech stack strip ────────────────────────────────── */}
      <div style={{
        padding:"16px 24px", borderRadius:12,
        background:t.surface, border:`1.5px solid ${t.border}`,
        display:"flex", gap:24, alignItems:"center", flexWrap:"wrap",
        marginBottom:20,
      }}>
        <span style={{ fontSize:10, color:t.muted, fontWeight:800, textTransform:"uppercase", letterSpacing:"0.1em", flexShrink:0 }}>
          Powered by
        </span>
        {["Llama-3 8B","RTX 4050 GPU","ChromaDB","IndianKanoon API","BSA 2023","Ollama"].map(l => (
          <span key={l} style={{ fontSize:12, color:t.sub, fontWeight:600 }}>{l}</span>
        ))}
      </div>

      {/* ── Disclaimer ─────────────────────────────────────── */}
      <div style={{
        padding:"14px 20px", borderRadius:12,
        background:t.amberDim, border:`1px solid ${t.amber}33`,
        display:"flex", gap:12, alignItems:"flex-start",
      }}>
        <Ic d={ICONS.alert} size={15} color={t.amber} sw={2} />
        <p style={{ fontSize:12, color:t.amber, margin:0, lineHeight:1.7 }}>
          <strong>Disclaimer:</strong> NyayaSetu provides AI-generated legal guidance for informational purposes only.
          It does not constitute legal advice. For important legal matters, consult a qualified Indian advocate.
        </p>
      </div>

      <style>{`
        @media (max-width:640px) { .stat-grid{grid-template-columns:repeat(2,1fr)!important;} }
      `}</style>
    </div>
  );
}