"""
Compliance Checker Page
website/pages/3_compliance_check.py

IPC → BNS migration checker with compliance score 0-100
"""

import streamlit as st
import sys, os, io
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
    IPC_TO_BNS,
)
import fitz

st.set_page_config(page_title="Compliance Checker — Nyaya-Setu", page_icon="✅", layout="wide")

st.markdown("""
<style>
.mapping-row { display:flex; gap:1rem; align-items:center; padding:0.5rem 0.8rem; border-radius:8px; margin:0.3rem 0; background:#F8F9FC; }
.old-section { font-family:monospace; background:#FDE8E8; color:#8B0000; padding:2px 8px; border-radius:4px; font-size:0.85rem; }
.new-section { font-family:monospace; background:#E6F4EC; color:#1A6B3C; padding:2px 8px; border-radius:4px; font-size:0.85rem; }
.abolished   { font-family:monospace; background:#1B3A6B; color:#fff;    padding:2px 8px; border-radius:4px; font-size:0.85rem; }
.score-A { color:#1A6B3C; }
.score-B { color:#2E5FA3; }
.score-C { color:#C8960C; }
.score-F { color:#8B0000; }
</style>
""", unsafe_allow_html=True)

st.title("✅ BNS Compliance Checker")
st.caption("Check if your legal document uses obsolete IPC/CrPC/Evidence Act sections. India's new laws took effect July 1, 2024.")

# ── Info banner ────────────────────────────────────────────────────────────────
with st.expander("ℹ️ Why does this matter?"):
    st.markdown("""
    **Three major Indian laws changed on July 1, 2024:**

    | Old law | New law | What changed |
    |---------|---------|--------------|
    | Indian Penal Code (IPC) 1860 | Bharatiya Nyaya Sanhita (BNS) 2023 | All IPC sections renumbered |
    | Code of Criminal Procedure (CrPC) | Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 | All CrPC sections renumbered |
    | Indian Evidence Act | Bharatiya Sakshya Adhiniyam (BSA) 2023 | Evidence rules updated |

    **IPC Section 309** (attempt to suicide) was **abolished** — it no longer exists.
    Courts can reject petitions citing obsolete IPC sections on technical grounds.
    """)

# ── Input ──────────────────────────────────────────────────────────────────────
tab_upload, tab_text, tab_lookup = st.tabs(["📄 Upload Document", "📝 Paste Text", "🔍 Section Lookup"])

doc_text = ""

with tab_upload:
    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded:
        with st.spinner("Extracting text..."):
            doc_text = extract_text_from_pdf_bytes(uploaded.read())
        st.success(f"Extracted {len(doc_text):,} characters")

with tab_text:
    doc_text_input = st.text_area("Paste your document text:",
        height=200,
        placeholder="The accused is charged under IPC 420 and IPC 506...")
    if doc_text_input:
        doc_text = doc_text_input

with tab_lookup:
    st.markdown("**Look up any IPC/CrPC section's BNS equivalent:**")
    col_l, col_r = st.columns(2)
    with col_l:
        lookup_act = st.selectbox("Act:", ["IPC", "CrPC", "IEA"])
        lookup_num = st.text_input("Section number:", placeholder="e.g. 420")
    with col_r:
        if lookup_num:
            key = f"{lookup_act} {lookup_num.upper()}"
            mapping = IPC_TO_BNS.get(key)
            if mapping:
                if mapping["bns"] == "ABOLISHED":
                    st.error(f"❌ **{key}** has been ABOLISHED under BNS 2023.\n\n{mapping['name']}")
                else:
                    st.success(f"✅ **{key}** → **{mapping['bns']}**\n\n{mapping['name']}")
            else:
                st.info(f"Section {key} not in mapping table. Check indiacode.nic.in for the official BNS equivalent.")

    st.markdown("---")
    st.markdown("**Quick reference — common mappings:**")
    common = [
        ("IPC 420","BNS 318","Cheating"),
        ("IPC 302","BNS 101","Murder"),
        ("IPC 307","BNS 109","Attempt to murder"),
        ("IPC 354","BNS 74", "Outraging modesty"),
        ("IPC 375","BNS 63", "Rape"),
        ("IPC 498A","BNS 85","Cruelty by husband"),
        ("IPC 509","BNS 79", "Insulting modesty"),
        ("IPC 309","ABOLISHED","Attempt to suicide — removed"),
        ("CrPC 154","BNSS 173","FIR registration"),
        ("CrPC 438","BNSS 482","Anticipatory bail"),
        ("IEA 65B","BSA 63","Electronic evidence"),
    ]
    for old, new, name in common:
        abolished = new == "ABOLISHED"
        st.markdown(f"""
        <div class="mapping-row">
            <span class="old-section">{old}</span>
            <span style="color:#64748b;">→</span>
            <span class="{'abolished' if abolished else 'new-section'}">{new}</span>
            <span style="color:#64748b;font-size:0.85rem;">{name}</span>
        </div>
        """, unsafe_allow_html=True)


# ── Compliance analysis ────────────────────────────────────────────────────────
if doc_text and len(doc_text.strip()) > 20:
    st.divider()

    if st.button("Run Compliance Check", type="primary"):
        with st.spinner("Scanning document..."):
            result = compute_compliance_score(doc_text)

        score    = result["score"]
        grade    = result["grade"]
        mappings = result["report"]["mappings"]
        obsolete = result["report"]["obsolete"]

        # ── Score display ──────────────────────────────────────────────────────
        col_score, col_grade, col_note = st.columns([2, 1, 3])

        with col_score:
            st.metric("Compliance Score", f"{score}/100")
            st.progress(score / 100)

        with col_grade:
            grade_bg = {"A":"#1A6B3C","B":"#2E5FA3","C":"#C8960C","F":"#8B0000"}.get(grade,"#64748b")
            st.markdown(f"""
            <div style="text-align:center;padding:1rem;background:{grade_bg};color:white;
                        border-radius:10px;font-size:2.5rem;font-weight:700;">{grade}</div>
            """, unsafe_allow_html=True)

        with col_note:
            if score == 100:
                st.success(result["note"])
            elif score >= 70:
                st.info(result["note"])
            elif score >= 50:
                st.warning(result["note"])
            else:
                st.error(result["note"])

            if obsolete:
                st.error(f"⚠️ {len(obsolete)} abolished section(s) cited — these no longer exist under BNS 2023.")

        # ── Mappings ───────────────────────────────────────────────────────────
        if mappings:
            st.markdown("---")
            st.markdown("### Required corrections")
            st.caption("Replace these obsolete references before filing.")

            for m in mappings:
                abolished = m["new"] == "ABOLISHED"
                icon      = "❌" if abolished else "✅"

                col_a, col_b, col_c = st.columns([2, 2, 4])
                with col_a:
                    st.markdown(f'<span class="old-section">{m["old"]}</span>', unsafe_allow_html=True)
                with col_b:
                    css = "abolished" if abolished else "new-section"
                    st.markdown(f'<span class="{css}">{m["new"]}</span>', unsafe_allow_html=True)
                with col_c:
                    st.markdown(f'<span style="font-size:0.9rem;color:#475569;">{icon} {m["name"]}</span>', unsafe_allow_html=True)

        else:
            st.success("No obsolete IPC/CrPC references found in this document.")

        # ── Download corrected version hint ───────────────────────────────────
        if mappings:
            st.markdown("---")
            corrected = doc_text
            for m in mappings:
                if m["new"] != "ABOLISHED":
                    corrected = corrected.replace(m["old"], m["new"])

            st.download_button(
                "⬇️ Download auto-corrected text",
                data=corrected,
                file_name="document_bns_corrected.txt",
                mime="text/plain",
                help="IPC/CrPC references replaced with BNS/BNSS equivalents. Review before using."
            )
            st.caption("⚠️ Auto-correction is a starting point. Always have a legal professional review before filing.")
