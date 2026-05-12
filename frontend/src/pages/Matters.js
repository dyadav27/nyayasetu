import React, { useState } from "react";
import { PageTitle, Card, Btn, Input, Ic, ICONS, Tag } from "../components/UI";

export default function Matters({ t, toast }) {
  const [viewMode, setViewMode] = useState("list");
  const [search, setSearch] = useState("");

  const stats = [
    { label: "Total Cases", value: "0", bg: t.text, fg: t.bg },
    { label: "Pending", value: "0", bg: t.surface, fg: t.text },
    { label: "Disposed", value: "0", bg: t.surface, fg: t.text },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", padding: "0 24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Matters</h1>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Active litigations, filings, and advisory</p>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          {/* View Toggles */}
          <div style={{ display: "flex", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: 4 }}>
            {["List", "Cards", "Board"].map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m.toLowerCase())}
                style={{
                  background: viewMode === m.toLowerCase() ? (t === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)") : "transparent",
                  color: viewMode === m.toLowerCase() ? t.text : t.sub,
                  border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600,
                  cursor: "pointer", transition: "all 0.2s"
                }}
              >
                {m}
              </button>
            ))}
          </div>
          <Btn t={t}>+ New Matter</Btn>
        </div>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 14, top: 12, opacity: 0.5 }}>
            <Ic d={ICONS.search} size={16} color={t.text} />
          </div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search matters..."
            style={{
              width: "100%", padding: "12px 16px 12px 40px", borderRadius: 10,
              background: t.surface, border: `1px solid ${t.border}`,
              color: t.text, fontSize: 14, outline: "none",
              transition: "border-color 0.2s", fontFamily: "inherit"
            }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 32 }}>
        {stats.map((s, i) => (
          <div key={i} style={{
            background: s.bg, color: s.fg,
            padding: "16px 20px", borderRadius: 12,
            border: `1px solid ${t.border}`,
            minWidth: 140, display: "flex", flexDirection: "column", gap: 4
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", opacity: 0.7 }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 800 }}>{s.value}</div>
          </div>
        ))}
        <button style={{
          width: 50, borderRadius: 12, border: `1px dashed ${t.border}`,
          background: "transparent", color: t.sub, display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer", fontSize: 24
        }}>+</button>
      </div>

      {/* Empty State */}
      <div style={{
        background: t.surface, border: `1px solid ${t.border}`, borderRadius: 16,
        padding: "80px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"
      }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: t.surfaceUp, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
          <Ic d={ICONS.file} size={24} color={t.sub} />
        </div>
        <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px", color: t.text }}>No matters yet.</h3>
        <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Create your first matter to get started.</p>
      </div>

    </div>
  );
}
