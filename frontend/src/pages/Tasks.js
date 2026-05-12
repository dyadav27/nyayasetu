import React, { useState } from "react";
import { Btn, Ic, ICONS } from "../components/UI";

export default function Tasks({ t, toast }) {
  const [tab, setTab] = useState("Tasks");

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", padding: "0 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Tasks</h1>
        <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Manage tasks and workflows across all matters</p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: `1px solid ${t.border}`, marginBottom: 24, gap: 24 }}>
        {["Tasks", "Task Templates"].map(m => (
          <button
            key={m}
            onClick={() => setTab(m)}
            style={{
              background: "transparent",
              color: tab === m ? t.text : t.sub,
              border: "none",
              borderBottom: tab === m ? `2px solid ${t.text}` : "2px solid transparent",
              padding: "0 4px 12px",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
              fontFamily: "inherit"
            }}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", gap: 16 }}>
            {/* Status dropdown mockup */}
            <div style={{ position: "relative" }}>
              <select style={{
                appearance: "none", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8,
                padding: "8px 36px 8px 16px", color: t.text, fontSize: 14, outline: "none", cursor: "pointer",
                fontFamily: "inherit", minWidth: 160
              }}>
                <option>All statuses</option>
                <option>Pending</option>
                <option>Done</option>
              </select>
              <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", opacity: 0.5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
            </div>
            
            {/* Priority dropdown mockup */}
            <div style={{ position: "relative" }}>
              <select style={{
                appearance: "none", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8,
                padding: "8px 36px 8px 16px", color: t.text, fontSize: 14, outline: "none", cursor: "pointer",
                fontFamily: "inherit", minWidth: 160
              }}>
                <option>All priorities</option>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
              <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", opacity: 0.5 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
            </div>
          </div>
          <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12 }}>
            <span>0 pending</span>
            <span>0 done</span>
          </div>
        </div>

        <Btn t={t}>+ Add Task</Btn>
      </div>

      {/* Empty State */}
      <div style={{
        padding: "80px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"
      }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: t.surfaceUp, border: `1px solid ${t.border}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
          <Ic d={ICONS.check} size={24} color={t.sub} />
        </div>
        <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px", color: t.text }}>No tasks found</h3>
        <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Create a task or adjust the filters above.</p>
      </div>

    </div>
  );
}
