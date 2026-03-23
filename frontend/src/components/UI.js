import { useState, useRef, useEffect } from "react";

// ─── Palette ──────────────────────────────────────────────────────────────────
export const DARK = {
  bg:          "#080c14",
  surface:     "#0e1420",
  surfaceUp:   "#141b2d",
  border:      "#1e2a42",
  borderHover: "#2e4070",
  text:        "#e8edf8",
  sub:         "#6b7fa8",
  muted:       "#2a3550",
  blue:        "#4d7cfe",
  blueDim:     "#0d1f52",
  green:       "#34d399",
  greenDim:    "#052e1c",
  red:         "#f87171",
  redDim:      "#2d0808",
  amber:       "#fbbf24",
  amberDim:    "#2d1f05",
  gold:        "#d4a843",
  goldDim:     "#2a1e06",
  nav:         "rgba(8,12,20,0.96)",
};

export const LIGHT = {
  bg:          "#f4f6fb",
  surface:     "#ffffff",
  surfaceUp:   "#eef1fa",
  border:      "#dae0f0",
  borderHover: "#a8b8d8",
  text:        "#0d1420",
  sub:         "#4a5a7a",
  muted:       "#bcc8e0",
  blue:        "#2558e8",
  blueDim:     "#dce8ff",
  green:       "#059669",
  greenDim:    "#d1fae5",
  red:         "#dc2626",
  redDim:      "#fee2e2",
  amber:       "#b45309",
  amberDim:    "#fef3c7",
  gold:        "#92640a",
  goldDim:     "#fefce8",
  nav:         "rgba(244,246,251,0.96)",
};

// ─── Icons ────────────────────────────────────────────────────────────────────
export const Ic = ({ d, size = 16, color = "currentColor", sw = 1.75 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
    style={{ flexShrink: 0 }}>
    {typeof d === "string" ? <path d={d} /> : d}
  </svg>
);

export const ICONS = {
  home:     "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z",
  doc:      [<path key="a" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>,<polyline key="b" points="14,2 14,8 20,8"/>],
  shield:   "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  camera:   [<path key="a" d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>,<circle key="b" cx="12" cy="13" r="4"/>],
  search:   [<circle key="a" cx="11" cy="11" r="8"/>,<line key="b" x1="21" y1="21" x2="16.65" y2="16.65"/>],
  sun:      [<circle key="a" cx="12" cy="12" r="5"/>,...[0,45,90,135,180,225,270,315].map((a,i)=>{const r=a*Math.PI/180;return <line key={i} x1={12+7*Math.sin(r)} y1={12-7*Math.cos(r)} x2={12+9*Math.sin(r)} y2={12-9*Math.cos(r)}/>;})],
  moon:     "M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z",
  menu:     [<line key="a" x1="3" y1="6" x2="21" y2="6"/>,<line key="b" x1="3" y1="12" x2="21" y2="12"/>,<line key="c" x1="3" y1="18" x2="21" y2="18"/>],
  x:        [<line key="a" x1="18" y1="6" x2="6" y2="18"/>,<line key="b" x1="6" y1="6" x2="18" y2="18"/>],
  upload:   [<polyline key="a" points="16,16 12,12 8,16"/>,<line key="b" x1="12" y1="12" x2="12" y2="21"/>,<path key="c" d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/>],
  arrow:    [<line key="a" x1="5" y1="12" x2="19" y2="12"/>,<polyline key="b" points="12,5 19,12 12,19"/>],
  check:    <polyline points="20,6 9,17 4,12"/>,
  alert:    [<polygon key="a" points="10.29,3.86 1.82,18 22.18,18 13.71,3.86"/>,<line key="b" x1="12" y1="9" x2="12" y2="13"/>,<line key="c" x1="12" y1="17" x2="12.01" y2="17"/>],
  spin:     [<line key="a" x1="12" y1="2" x2="12" y2="6"/>,<line key="b" x1="12" y1="18" x2="12" y2="22"/>,<line key="c" x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>,<line key="d" x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>,<line key="e" x1="2" y1="12" x2="6" y2="12"/>,<line key="f" x1="18" y1="12" x2="22" y2="12"/>,<line key="g" x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>,<line key="h" x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>],
  scale:    [<line key="a" x1="12" y1="1" x2="12" y2="23"/>,<path key="b" d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>],
  external: [<path key="a" d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>,<polyline key="b" points="15,3 21,3 21,9"/>,<line key="c" x1="10" y1="14" x2="21" y2="3"/>],
  info:     [<circle key="a" cx="12" cy="12" r="10"/>,<line key="b" x1="12" y1="16" x2="12" y2="12"/>,<line key="c" x1="12" y1="8" x2="12.01" y2="8"/>],
  download: [<path key="a" d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>,<polyline key="b" points="7,10 12,15 17,10"/>,<line key="c" x1="12" y1="15" x2="12" y2="3"/>],
  file:     [<path key="a" d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/>,<polyline key="b" points="13,2 13,9 20,9"/>],
};

// ─── Spinner ──────────────────────────────────────────────────────────────────
export const Spinner = ({ c, size = 15 }) => (
  <span style={{ display:"inline-flex", animation:"spin 1s linear infinite" }}>
    <Ic d={ICONS.spin} size={size} color={c} />
  </span>
);

// ─── Tag / Badge ──────────────────────────────────────────────────────────────
export const Tag = ({ label, variant, t }) => {
  const map = {
    success: { bg: t.greenDim, fg: t.green },
    danger:  { bg: t.redDim,   fg: t.red },
    warning: { bg: t.amberDim, fg: t.amber },
    info:    { bg: t.blueDim,  fg: t.blue },
    gold:    { bg: t.goldDim,  fg: t.gold },
  };
  const s = map[variant] || map.info;
  return (
    <span style={{
      padding:"2px 10px", borderRadius:99, fontSize:11, fontWeight:700,
      background:s.bg, color:s.fg, letterSpacing:"0.02em", whiteSpace:"nowrap",
      border:`1px solid ${s.fg}25`,
    }}>{label}</span>
  );
};

// ─── Button ───────────────────────────────────────────────────────────────────
export const Btn = ({ onClick, disabled, loading, children, small, outline, danger, t }) => {
  const bg = disabled ? t.surfaceUp : danger ? t.red : outline ? "transparent" : t.blue;
  const fg = disabled ? t.sub : outline ? t.sub : "#fff";
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: small ? "8px 18px" : "10px 24px",
      borderRadius:9, fontSize:13, fontWeight:700, fontFamily:"inherit",
      cursor: disabled ? "not-allowed" : "pointer",
      border: outline ? `1.5px solid ${t.border}` : "none",
      background:bg, color:fg,
      display:"inline-flex", alignItems:"center", gap:7,
      transition:"all 0.18s",
      opacity: disabled ? 0.5 : 1,
      letterSpacing:"0.02em",
      boxShadow: (!disabled && !outline) ? `0 4px 14px ${danger ? t.red : t.blue}44` : "none",
    }}
      onMouseEnter={e => { if(!disabled) e.currentTarget.style.transform="translateY(-1px)"; }}
      onMouseLeave={e => { e.currentTarget.style.transform="translateY(0)"; }}
    >
      {loading && <Spinner c={fg} />}
      {children}
    </button>
  );
};

// ─── Input ────────────────────────────────────────────────────────────────────
export const Input = ({ value, onChange, onKeyDown, placeholder, t }) => (
  <input value={value} onChange={onChange} onKeyDown={onKeyDown} placeholder={placeholder}
    style={{
      background:t.surfaceUp, border:`1.5px solid ${t.border}`,
      borderRadius:9, padding:"10px 16px", color:t.text,
      fontSize:14, fontFamily:"inherit", outline:"none", width:"100%",
      transition:"border-color 0.15s, box-shadow 0.15s",
    }}
  />
);

// ─── Textarea ─────────────────────────────────────────────────────────────────
export const Textarea = ({ value, onChange, placeholder, rows, t }) => (
  <textarea value={value} onChange={onChange} placeholder={placeholder} rows={rows || 5}
    style={{
      background:t.surfaceUp, border:`1.5px solid ${t.border}`,
      borderRadius:9, padding:"12px 16px", color:t.text,
      fontSize:14, fontFamily:"inherit", outline:"none", width:"100%",
      resize:"vertical", lineHeight:1.7,
      transition:"border-color 0.15s",
    }}
  />
);

// ─── Card ─────────────────────────────────────────────────────────────────────
export const Card = ({ children, t, style, hover }) => {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => hover && setHov(true)}
      onMouseLeave={() => hover && setHov(false)}
      style={{
        background:t.surface, border:`1.5px solid ${hov ? t.borderHover : t.border}`,
        borderRadius:14, padding:"24px 28px",
        transition:"border-color 0.2s, transform 0.2s, box-shadow 0.2s",
        transform: hov ? "translateY(-2px)" : "translateY(0)",
        boxShadow: hov ? `0 8px 32px ${t.blue}18` : "none",
        ...style,
      }}>
      {children}
    </div>
  );
};

// ─── Section Title ────────────────────────────────────────────────────────────
export const SectionTitle = ({ children, t }) => (
  <h3 style={{
    fontSize:11, fontWeight:800, color:t.sub,
    letterSpacing:"0.1em", textTransform:"uppercase", margin:"0 0 16px",
  }}>{children}</h3>
);

// ─── Page Header ─────────────────────────────────────────────────────────────
export const PageTitle = ({ icon, title, desc, badge, t }) => (
  <div style={{ marginBottom:40 }}>
    <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:10 }}>
      <div style={{
        width:42, height:42, borderRadius:12,
        background:`linear-gradient(135deg, ${t.blue}22, ${t.blue}44)`,
        border:`1px solid ${t.blue}33`,
        display:"flex", alignItems:"center", justifyContent:"center",
      }}>
        <Ic d={ICONS[icon]} size={19} color={t.blue} />
      </div>
      <div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <h1 style={{ fontSize:22, fontWeight:800, color:t.text, margin:0, letterSpacing:"-0.02em" }}>
            {title}
          </h1>
          {badge && <Tag label={badge} variant="gold" t={t} />}
        </div>
      </div>
    </div>
    <p style={{ fontSize:14, color:t.sub, margin:"0 0 0 54px", lineHeight:1.7, maxWidth:560 }}>{desc}</p>
  </div>
);

// ─── Error Box ────────────────────────────────────────────────────────────────
export const ErrBox = ({ msg, t }) => (
  <div style={{
    padding:"12px 18px", borderRadius:10, background:t.redDim,
    border:`1px solid ${t.red}44`, color:t.red, fontSize:13,
    display:"flex", gap:10, alignItems:"flex-start", marginBottom:16,
    animation:"fadeUp 0.2s ease",
  }}>
    <Ic d={ICONS.alert} size={15} color={t.red} sw={2} />
    <span style={{ lineHeight:1.5 }}>{msg}</span>
  </div>
);

// ─── Drop Zone ────────────────────────────────────────────────────────────────
export const DropZone = ({ onFile, accept, hint, t }) => {
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState(null);
  const ref = useRef();
  const pick = (f) => { if(f) { setFile(f); onFile(f); } };

  return (
    <div
      onClick={() => ref.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
      style={{
        border:`2px dashed ${drag ? t.blue : t.border}`,
        borderRadius:12, padding:"32px 24px", textAlign:"center",
        cursor:"pointer", background: drag ? `${t.blue}10` : t.surfaceUp,
        transition:"all 0.2s",
        position:"relative", overflow:"hidden",
      }}
    >
      <input ref={ref} type="file" accept={accept} style={{ display:"none" }}
        onChange={(e) => pick(e.target.files[0])} />

      {/* Background pattern */}
      <div style={{
        position:"absolute", inset:0, opacity:0.03,
        backgroundImage:`radial-gradient(circle, ${t.blue} 1px, transparent 1px)`,
        backgroundSize:"20px 20px",
        pointerEvents:"none",
      }}/>

      <div style={{ position:"relative" }}>
        <div style={{
          width:52, height:52, borderRadius:14,
          background:`linear-gradient(135deg, ${t.blue}22, ${t.blue}44)`,
          border:`1px solid ${t.blue}33`,
          display:"flex", alignItems:"center", justifyContent:"center",
          margin:"0 auto 14px",
          transform: drag ? "scale(1.1)" : "scale(1)",
          transition:"transform 0.2s",
        }}>
          <Ic d={ICONS.upload} size={22} color={t.blue} />
        </div>

        {file ? (
          <div>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
              <Ic d={ICONS.file} size={15} color={t.green} />
              <span style={{ fontSize:14, fontWeight:700, color:t.green }}>{file.name}</span>
            </div>
            <p style={{ fontSize:12, color:t.sub, margin:"4px 0 0" }}>
              {(file.size/1024).toFixed(0)} KB · Click to replace
            </p>
          </div>
        ) : (
          <>
            <p style={{ fontSize:14, fontWeight:700, color:t.text, margin:"0 0 4px" }}>
              Drop file here or <span style={{ color:t.blue }}>browse</span>
            </p>
            <p style={{ fontSize:12, color:t.sub, margin:0 }}>{hint}</p>
          </>
        )}
      </div>
    </div>
  );
};

// ─── Progress bar ──────────────────────────────────────────────────────────────
export const ProgressBar = ({ value, color, t }) => (
  <div style={{ height:4, borderRadius:2, background:t.muted, overflow:"hidden" }}>
    <div style={{
      width:`${Math.round(value*100)}%`, height:"100%",
      background:color, borderRadius:2,
      transition:"width 0.6s cubic-bezier(0.4,0,0.2,1)",
    }}/>
  </div>
);

// ─── Divider ──────────────────────────────────────────────────────────────────
export const Divider = ({ t, label }) => (
  <div style={{ display:"flex", alignItems:"center", gap:12, margin:"20px 0" }}>
    <div style={{ flex:1, height:1, background:t.border }}/>
    {label && <span style={{ fontSize:10, color:t.muted, fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase", whiteSpace:"nowrap" }}>
      {label}
    </span>}
    <div style={{ flex:1, height:1, background:t.border }}/>
  </div>
);

// ─── Animated number ──────────────────────────────────────────────────────────
export const AnimNum = ({ target }) => {
  const [v, setV] = useState(0);
  const n = parseInt(String(target).replace(/\D/g,"")) || 0;
  useEffect(() => {
    if (!n) return;
    let cur = 0; const step = Math.max(1, Math.ceil(n/50));
    const id = setInterval(() => {
      cur += step; if (cur >= n) { setV(n); clearInterval(id); } else setV(cur);
    }, 20);
    return () => clearInterval(id);
  }, [n]);
  return <span>{String(target).replace(n, v.toLocaleString())}</span>;
};

// ─── Toast ────────────────────────────────────────────────────────────────────
export const Toast = ({ msg, type, t, onClose }) => {
  const c = type==="success" ? t.green : type==="error" ? t.red : t.amber;
  return (
    <div style={{
      position:"fixed", bottom:24, right:24, zIndex:9999,
      background:t.surface, border:`1.5px solid ${t.border}`,
      borderLeft:`3px solid ${c}`, borderRadius:12,
      padding:"14px 20px", maxWidth:360, minWidth:260,
      boxShadow:`0 16px 48px rgba(0,0,0,0.4)`,
      display:"flex", alignItems:"center", gap:12,
      animation:"slideUp 0.3s cubic-bezier(0.34,1.56,0.64,1)",
    }}>
      <div style={{
        width:28, height:28, borderRadius:8, flexShrink:0,
        background:`${c}22`, display:"flex", alignItems:"center", justifyContent:"center",
      }}>
        <Ic d={type==="success" ? ICONS.check : ICONS.alert} size={13} color={c} sw={2.5} />
      </div>
      <span style={{ color:t.text, fontSize:13, fontWeight:500, flex:1, lineHeight:1.5 }}>{msg}</span>
      <button onClick={onClose} style={{
        background:"none", border:"none", cursor:"pointer", color:t.sub,
        padding:2, display:"flex", flexShrink:0,
        transition:"color 0.15s",
      }}>
        <Ic d={ICONS.x} size={13} />
      </button>
    </div>
  );
};