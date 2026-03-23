import { useState } from "react";
import { useLocation, Link } from "react-router-dom";

const NAV_LINKS = [
  { path: "/",           label: "Home",          icon: "🏛️" },
  { path: "/analyze",    label: "Analyze Doc",   icon: "📄" },
  { path: "/compliance", label: "BNS Compliance",icon: "⚖️" },
  { path: "/evidence",   label: "Evidence Cert", icon: "🔐" },
];

export default function Navbar() {
  const location = useLocation();
  const [open, setOpen]   = useState(false);
  const [dark, setDark]   = useState(true);

  const toggleDark = () => {
    setDark(!dark);
    document.body.setAttribute("data-theme", dark ? "light" : "dark");
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap');

        [data-theme="dark"], :root {
          --nb-surface: rgba(13,17,23,0.96);
          --nb-border:  rgba(255,255,255,0.09);
          --nb-text:    #e6edf3;
          --nb-sub:     rgba(230,237,243,0.55);
          --nb-hover:   rgba(255,255,255,0.07);
          --nb-active:  rgba(79,128,255,0.18);
          --nb-blue:    #5b8fff;
          --nb-gold:    #f0a500;
        }
        [data-theme="light"] {
          --nb-surface: rgba(255,255,255,0.95);
          --nb-border:  rgba(0,0,0,0.09);
          --nb-text:    #1B3A6B;
          --nb-sub:     #6B7280;
          --nb-hover:   rgba(27,58,107,0.06);
          --nb-active:  rgba(46,95,163,0.12);
          --nb-blue:    #2E5FA3;
          --nb-gold:    #C8960C;
        }

        .ns-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
          height: 70px;
          background: var(--nb-surface);
          backdrop-filter: blur(20px) saturate(180%);
          -webkit-backdrop-filter: blur(20px) saturate(180%);
          border-bottom: 1px solid var(--nb-border);
          display: flex; align-items: center;
          padding: 0 32px;
          justify-content: space-between;
          font-family: 'Outfit', system-ui, sans-serif;
        }

        /* ── Brand ── */
        .ns-brand {
          display: flex; align-items: center; gap: 11px;
          text-decoration: none; user-select: none;
        }
        .ns-brand-icon {
          width: 40px; height: 40px; border-radius: 11px;
          background: linear-gradient(135deg, #5b8fff 0%, #1B3A6B 100%);
          display: flex; align-items: center; justify-content: center;
          font-size: 19px; flex-shrink: 0;
          box-shadow: 0 3px 12px rgba(91,143,255,0.4);
        }
        .ns-brand-name {
          font-size: 22px; font-weight: 900; color: var(--nb-text);
          letter-spacing: -0.03em; line-height: 1;
        }
        .ns-brand-name span { color: var(--nb-gold); }
        .ns-brand-sub {
          font-size: 10px; color: var(--nb-sub); font-weight: 600;
          letter-spacing: 0.08em; text-transform: uppercase;
          margin-top: 3px;
        }

        /* ── Links ── */
        .ns-links {
          display: flex; align-items: center; gap: 4px;
        }
        .ns-link {
          display: flex; align-items: center; gap: 7px;
          padding: 9px 18px; border-radius: 10px;
          font-size: 15px; font-weight: 600;
          color: var(--nb-sub);
          text-decoration: none;
          transition: all 0.15s ease;
          white-space: nowrap;
          border: 1px solid transparent;
          font-family: 'Outfit', system-ui, sans-serif;
          letter-spacing: -0.01em;
        }
        .ns-link:hover {
          background: var(--nb-hover);
          color: var(--nb-text);
        }
        .ns-link.active {
          background: var(--nb-active);
          color: var(--nb-blue);
          border-color: rgba(91,143,255,0.3);
        }
        .ns-link-icon { font-size: 15px; }

        /* ── Right ── */
        .ns-right {
          display: flex; align-items: center; gap: 10px;
        }
        .ns-pill {
          padding: 5px 13px; border-radius: 20px;
          background: linear-gradient(135deg, var(--nb-blue), #1B3A6B);
          color: white; font-size: 12px; font-weight: 700;
          letter-spacing: 0.05em; text-transform: uppercase;
          font-family: 'Outfit', system-ui, sans-serif;
          box-shadow: 0 2px 8px rgba(91,143,255,0.3);
        }
        .ns-btn-icon {
          width: 38px; height: 38px; border-radius: 10px;
          background: var(--nb-hover); border: 1px solid var(--nb-border);
          cursor: pointer; display: flex; align-items: center;
          justify-content: center; font-size: 16px;
          transition: all 0.15s; color: var(--nb-sub);
        }
        .ns-btn-icon:hover { background: var(--nb-active); }

        .ns-hamburger {
          display: none; background: none; border: none;
          cursor: pointer; color: var(--nb-sub);
          font-size: 24px; padding: 4px; line-height: 1;
        }

        /* ── Mobile drawer ── */
        .ns-drawer {
          position: fixed; top: 70px; left: 0; right: 0; z-index: 999;
          background: var(--nb-surface);
          backdrop-filter: blur(20px);
          border-bottom: 1px solid var(--nb-border);
          padding: 10px 16px 16px;
          display: flex; flex-direction: column; gap: 4px;
          font-family: 'Outfit', system-ui, sans-serif;
        }
        .ns-drawer-link {
          display: flex; align-items: center; gap: 12px;
          padding: 12px 16px; border-radius: 10px;
          font-size: 16px; font-weight: 600;
          color: var(--nb-sub); text-decoration: none;
          transition: all 0.12s;
        }
        .ns-drawer-link:hover  { background: var(--nb-hover); color: var(--nb-text); }
        .ns-drawer-link.active { background: var(--nb-active); color: var(--nb-blue); }

        .ns-spacer { height: 70px; }

        @media (max-width: 760px) {
          .ns-links { display: none; }
          .ns-pill  { display: none; }
          .ns-hamburger { display: block; }
          .ns-nav { padding: 0 20px; }
        }
      `}</style>

      <nav className="ns-nav">
        <Link to="/" className="ns-brand">
          <div className="ns-brand-icon">⚖️</div>
          <div>
            <div className="ns-brand-name">Nyaya<span>Setu</span></div>
            <div className="ns-brand-sub">Bridge to Justice</div>
          </div>
        </Link>

        <div className="ns-links">
          {NAV_LINKS.map(l => (
            <Link
              key={l.path}
              to={l.path}
              className={`ns-link ${location.pathname === l.path ? "active" : ""}`}
            >
              <span className="ns-link-icon">{l.icon}</span>
              {l.label}
            </Link>
          ))}
        </div>

        <div className="ns-right">
          <span className="ns-pill">BNS 2023</span>
          <button className="ns-btn-icon" onClick={toggleDark} title="Toggle theme">
            {dark ? "☀️" : "🌙"}
          </button>
          <button className="ns-hamburger" onClick={() => setOpen(!open)}>
            {open ? "✕" : "☰"}
          </button>
        </div>
      </nav>

      {open && (
        <div className="ns-drawer">
          {NAV_LINKS.map(l => (
            <Link
              key={l.path}
              to={l.path}
              className={`ns-drawer-link ${location.pathname === l.path ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              <span>{l.icon}</span>{l.label}
            </Link>
          ))}
        </div>
      )}

      <div className="ns-spacer" />
    </>
  );
}