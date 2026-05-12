import React, { useState } from "react";
import { Btn, Card, Ic, ICONS } from "../components/UI";

export default function Calendar({ t, toast }) {
  const [viewMode, setViewMode] = useState("Month");

  // A simple mockup of a calendar grid for May 2026
  const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  
  // Padding days for April (26, 27, 28, 29, 30)
  const prevDays = [26, 27, 28, 29, 30];
  const currentDays = Array.from({ length: 31 }, (_, i) => i + 1);
  const nextDays = [1, 2, 3, 4, 5, 6];

  const renderCell = (num, isCurrentMonth) => {
    return (
      <div key={`${isCurrentMonth}-${num}`} style={{
        minHeight: 100,
        padding: "8px 12px",
        borderRight: `1px solid ${t.border}`,
        borderBottom: `1px solid ${t.border}`,
        color: isCurrentMonth ? t.text : t.sub,
        opacity: isCurrentMonth ? 1 : 0.4,
        fontSize: 13,
        fontWeight: 600,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        background: num === 9 && isCurrentMonth ? (t === "dark" ? "rgba(234, 88, 12, 0.1)" : "rgba(234, 88, 12, 0.05)") : "transparent"
      }}>
        <div style={{
          width: 24, height: 24, borderRadius: "50%",
          display: "flex", alignItems: "center", justifyContent: "center",
          background: num === 9 && isCurrentMonth ? "#ea580c" : "transparent",
          color: num === 9 && isCurrentMonth ? "#fff" : "inherit"
        }}>
          {num}
        </div>
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1200, margin: "40px auto", padding: "0 24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: t.text, margin: "0 0 6px" }}>Calendar</h1>
          <p style={{ fontSize: 14, color: t.sub, margin: 0 }}>Hearings & deadlines across all matters</p>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          {/* View Toggles */}
          <div style={{ display: "flex", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, padding: 4 }}>
            {["Month", "List"].map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                style={{
                  background: viewMode === m ? (t === "dark" ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)") : "transparent",
                  color: viewMode === m ? t.text : t.sub,
                  border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600,
                  cursor: "pointer", transition: "all 0.2s", display: "flex", alignItems: "center", gap: 6
                }}
              >
                {m === "Month" && <Ic d={ICONS.grid} size={14} color="inherit" />}
                {m === "List" && <Ic d={ICONS.menu} size={14} color="inherit" />}
                {m}
              </button>
            ))}
          </div>
          
          <button style={{
            background: "#ea580c", color: "#fff",
            border: "none", borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 700,
            cursor: "pointer", display: "flex", alignItems: "center", gap: 6, transition: "all 0.2s"
          }}>
            + Hearing
          </button>
          <Btn t={t}>+ Deadline</Btn>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 24 }}>
        {/* Calendar Grid area */}
        <Card t={t} style={{ padding: 0, overflow: "hidden" }}>
          {/* Month Navigation */}
          <div style={{ padding: "20px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${t.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <button style={{ background: "none", border: "none", cursor: "pointer", color: t.sub }}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></button>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, minWidth: 100, textAlign: "center" }}>May 2026</h2>
              <button style={{ background: "none", border: "none", cursor: "pointer", color: t.sub }}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
            </div>
            <button style={{
              background: "transparent", border: `1px solid ${t.border}`, borderRadius: 8,
              padding: "6px 14px", fontSize: 13, fontWeight: 600, color: t.text, cursor: "pointer"
            }}>Today</button>
          </div>

          {/* Days Header */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", borderBottom: `1px solid ${t.border}` }}>
            {days.map(d => (
              <div key={d} style={{ padding: "12px", textAlign: "center", fontSize: 11, fontWeight: 700, color: t.sub, letterSpacing: "0.05em", borderRight: `1px solid ${t.border}` }}>
                {d}
              </div>
            ))}
          </div>

          {/* Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
            {prevDays.map(d => renderCell(d, false))}
            {currentDays.map(d => renderCell(d, true))}
            {nextDays.map(d => renderCell(d, false))}
          </div>
        </Card>

        {/* Right Sidebar */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 24px", color: t.text }}>Select a date</h3>
          <div style={{ textAlign: "center", color: t.sub, marginTop: 40, fontSize: 14 }}>
            No events on this day
          </div>
        </div>
      </div>
    </div>
  );
}
