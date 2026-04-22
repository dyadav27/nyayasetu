import { Ic, ICONS } from "./UI";

const TOOLS = [
  { id: "analyzer", label: "Document Analyzer", desc: "Clause risk analysis" },
  { id: "compliance", label: "BNS Compliance", desc: "IPC → BNS 2023 migration" },
  { id: "evidence", label: "Evidence Certificate", desc: "BSA Section 63 SHA-256" },
  { id: "caselaws", label: "Case Laws", desc: "IndianKanoon search" },
];

const RESOURCES = [
  { label: "BNS 2023 — India Code", href: "https://indiacode.nic.in/bitstream/123456789/20062/1/bharatiya_nyaya_sanhita_2023.pdf" },
  { label: "BNSS 2023 — India Code", href: "https://indiacode.nic.in/bitstream/123456789/20063/1/bharatiya_nagarik_suraksha_sanhita_2023.pdf" },
  { label: "BSA 2023 — India Code", href: "https://indiacode.nic.in/bitstream/123456789/20064/1/bharatiya_sakshya_adhiniyam_2023.pdf" },
  { label: "IndianKanoon", href: "https://indiankanoon.org" },
  { label: "India Code", href: "https://indiacode.nic.in" },
];

const STACK = ["Llama-3 8B", "ChromaDB", "FastAPI", "React", "MiniLM + BM25", "ReportLab"];

// ── Scales SVG (same as nav, reused for consistency) ─────────────────────────
const ScalesIcon = ({ size = 18, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
    <rect x="15.2" y="3.5" width="1.6" height="21" rx="0.8" fill={color} opacity="0.9" />
    <rect x="8" y="24.5" width="16" height="2" rx="1" fill={color} opacity="0.8" />
    <rect x="5.5" y="26.5" width="21" height="1.4" rx="0.7" fill={color} opacity="0.55" />
    <rect x="3.5" y="7.5" width="25" height="1.8" rx="0.9" fill={color} opacity="0.9" />
    <circle cx="16" cy="4.5" r="1.8" fill={color} opacity="0.9" />
    <line x1="6.5" y1="9.3" x2="6.5" y2="15.5" stroke={color} strokeWidth="1.2" strokeLinecap="round" opacity="0.8" />
    <line x1="25.5" y1="9.3" x2="25.5" y2="15.5" stroke={color} strokeWidth="1.2" strokeLinecap="round" opacity="0.8" />
    <path d="M3 15.5 Q6.5 21 10 15.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.9" />
    <path d="M22 15.5 Q25.5 21 29 15.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.9" />
  </svg>
);

export default function Footer({ t, go }) {
  const year = new Date().getFullYear();
  const isDark = t.text === "#e2e8f4";

  return (
    <footer style={{
      background: isDark
        ? "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(6,8,14,0.6) 20%, #06080e 100%)"
        : "linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(245,247,252,0.6) 20%, #eef1f8 100%)",
      borderTop: `1px solid ${t.border}`,
      fontFamily: "'DM Sans', system-ui, sans-serif",
    }}>

      {/* ── Top divider strip ── */}
      <div style={{
        height: 3,
        background: `linear-gradient(90deg, transparent 0%, ${t.blue}55 30%, ${t.blue}aa 50%, ${t.blue}55 70%, transparent 100%)`,
      }} />

      {/* ── Main footer body ── */}
      <div style={{ maxWidth: 1060, margin: "0 auto", padding: "56px 24px 36px" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "1.8fr 1fr 1fr 1fr",
          gap: 40,
        }} className="footer-cols">

          {/* ── Col 1: Brand ── */}
          <div>
            {/* Logo mark */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div style={{
                width: 38, height: 38, borderRadius: 10,
                background: `linear-gradient(150deg, ${t.blue} 0%, #0d1e5a 100%)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0,
                boxShadow: `0 2px 12px ${t.blue}44, inset 0 1px 0 rgba(255,255,255,0.14)`,
              }}>
                <ScalesIcon size={18} color="#fff" />
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 900, color: t.text, letterSpacing: "-0.04em", lineHeight: 1.15 }}>
                  Nyaya<span style={{ color: t.blue }}>Setu</span>
                </div>
                <div style={{ fontSize: 8, color: t.muted, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                  Bridge to Justice
                </div>
              </div>
            </div>

            <p style={{ fontSize: 13, color: t.sub, lineHeight: 1.85, margin: "0 0 20px", maxWidth: 300 }}>
              AI-powered legal tools for Indian citizens — built on BNS, BNSS, and BSA 2023.
              Runs entirely on your machine. Zero data leaves your device.
            </p>

            {/* Tags */}
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 24 }}>
              {[
                { label: "BNS 2023", color: t.blue },
                { label: "Local LLM", color: "#34d399" },
                { label: "Open Build", color: "#a78bfa" },
              ].map(tag => (
                <span key={tag.label} style={{
                  padding: "3px 10px", borderRadius: 99,
                  fontSize: 10, fontWeight: 700,
                  background: `${tag.color}14`,
                  border: `1px solid ${tag.color}2a`,
                  color: tag.color, letterSpacing: "0.02em",
                }}>
                  {tag.label}
                </span>
              ))}
            </div>

            {/* Tech stack pills */}
            <div style={{ fontSize: 10, color: t.muted, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
              Powered by
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {STACK.map(s => (
                <span key={s} style={{
                  fontSize: 11, color: t.sub, fontWeight: 500,
                  padding: "2px 9px", borderRadius: 6,
                  background: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)",
                  border: `1px solid ${t.border}`,
                }}>
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* ── Col 2: Tools ── */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: t.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 18 }}>
              Tools
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {TOOLS.map(item => (
                <button key={item.id} onClick={() => go(item.id)} style={{
                  background: "none", border: "none", cursor: "pointer",
                  padding: 0, textAlign: "left",
                }}>
                  <div style={{
                    fontSize: 13, fontWeight: 600, color: t.sub,
                    transition: "color 0.15s", marginBottom: 1,
                    display: "flex", alignItems: "center", gap: 5,
                  }}
                    onMouseEnter={e => e.currentTarget.style.color = t.blue}
                    onMouseLeave={e => e.currentTarget.style.color = t.sub}
                  >
                    {item.label}
                    <Ic d={ICONS.arrow} size={10} color="inherit" />
                  </div>
                  <div style={{ fontSize: 11, color: t.muted }}>{item.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* ── Col 3: Legal Resources ── */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: t.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 18 }}>
              Legal Resources
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {RESOURCES.map(r => (
                <a key={r.label} href={r.href} target="_blank" rel="noreferrer" style={{
                  fontSize: 13, color: t.sub, textDecoration: "none",
                  fontWeight: 500, transition: "color 0.15s",
                  display: "flex", alignItems: "center", gap: 5,
                }}
                  onMouseEnter={e => e.currentTarget.style.color = t.blue}
                  onMouseLeave={e => e.currentTarget.style.color = t.sub}
                >
                  {r.label}
                  <Ic d={ICONS.external} size={10} color="inherit" />
                </a>
              ))}
            </div>
          </div>

          {/* ── Col 4: System ── */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: t.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 18 }}>
              System
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "GPU", val: "RTX 4050 6GB" },
                { label: "LLM", val: "Llama-3 8B" },
                { label: "KB", val: "3,254 chunks" },
                { label: "Backend", val: "FastAPI :8001" },
                { label: "Frontend", val: "React :3000" },
                { label: "WhatsApp", val: "Twilio sandbox" },
              ].map(row => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ fontSize: 11, color: t.muted, fontWeight: 700, flexShrink: 0 }}>{row.label}</span>
                  <span style={{ fontSize: 11, color: t.sub, fontWeight: 500, textAlign: "right" }}>{row.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div style={{ borderTop: `1px solid ${t.border}` }}>
        <div style={{
          maxWidth: 1060, margin: "0 auto",
          padding: "18px 24px",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          flexWrap: "wrap", gap: 12,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <ScalesIcon size={13} color={t.muted} />
            <span style={{ fontSize: 12, color: t.muted }}>
              © {year} NyayaSetu · Team IKS · SPIT CSE 2025–26
            </span>
          </div>
          <p style={{
            fontSize: 11, color: t.muted,
            maxWidth: 500, textAlign: "right", lineHeight: 1.6, margin: 0,
          }}>
            Informational purposes only. Not legal advice.
            Consult a qualified Indian advocate for legal matters.
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          .footer-cols { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 520px) {
          .footer-cols { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </footer>
  );
}