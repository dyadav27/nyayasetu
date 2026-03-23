"""
Case Chat Page
website/pages/2_case_chat.py

Interactive legal case chat using judge_engine.py
- Multi-turn conversation
- IRAC judgement display
- Citation verification
- Evidence upload integration
"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from judge_engine import JudgeEngine
from lex_validator import verify_citations
import re

st.set_page_config(page_title="Case Chat — Nyaya-Setu", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
.chat-user { background:#E8F0FB; border-radius:12px 12px 2px 12px; padding:0.8rem 1rem; margin:0.4rem 0; color:#1B3A6B; }
.chat-bot  { background:#F8F9FC; border:1px solid #E2E8F0; border-radius:2px 12px 12px 12px; padding:0.8rem 1rem; margin:0.4rem 0; white-space:pre-wrap; }
.judgement-box { background:#F0F4FF; border:2px solid #2E5FA3; border-radius:12px; padding:1.2rem 1.5rem; margin:0.8rem 0; }
.irac-section { background:#fff; border-left:3px solid #2E5FA3; padding:0.6rem 1rem; margin:0.5rem 0; border-radius:0 8px 8px 0; }
.irac-label { color:#1B3A6B; font-weight:700; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em; }
.section-badge { background:#1B3A6B; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; display:inline-block; margin:2px 2px; }
.strength-strong  { color:#1A6B3C; font-weight:700; }
.strength-moderate{ color:#C8960C; font-weight:700; }
.strength-weak    { color:#8B0000; font-weight:700; }
.verified-cite    { color:#1A6B3C; font-size:0.82rem; }
.unverified-cite  { color:#8B0000; font-size:0.82rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "judge"    not in st.session_state: st.session_state.judge    = None
if "messages" not in st.session_state: st.session_state.messages = []
if "started"  not in st.session_state: st.session_state.started  = False
if "done"     not in st.session_state: st.session_state.done     = False


# ── IRAC parser ───────────────────────────────────────────────────────────────
def parse_and_display_judgement(text: str):
    """Parse the judgement text and render it with rich formatting."""

    # Extract sections cited
    sections = re.findall(r'(?:BNS|BNSS|BSA)\s+(?:Section\s+)?\d+[A-Z]?(?:\(\d+\))?', text)
    if sections:
        verified = verify_citations(sections)

    # Display judgement box
    st.markdown('<div class="judgement-box">', unsafe_allow_html=True)
    st.markdown("### ⚖️ Legal Assessment")

    # Extract and display key parts
    lines = text.split('\n')
    current_section = None
    irac_parts = {"ISSUE": "", "RULE": "", "APPLICATION": "", "CONCLUSION": ""}
    steps = []
    other_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper() in ["ISSUE", "RULE", "APPLICATION", "CONCLUSION"]:
            current_section = line.upper()
        elif current_section and current_section in irac_parts:
            irac_parts[current_section] += line + " "
        elif re.match(r'^Steps?:', line, re.IGNORECASE):
            current_section = "STEPS"
        elif current_section == "STEPS" or re.match(r'^\d+\.', line):
            steps.append(re.sub(r'^\d+\.\s*', '', line))
        elif "Section:" in line or "Offence:" in line or "Punishment:" in line or "Type:" in line or "Case strength:" in line or "Reason:" in line:
            other_lines.append(line)
        elif "⚖️" not in line and "Legal Assessment" not in line:
            if not any(k in line for k in ["ISSUE","RULE","APPLICATION","CONCLUSION"]):
                other_lines.append(line)

    # Key facts display
    for line in other_lines:
        if any(k in line for k in ["Section:","Offence:","Punishment:","Type:","Case strength:","Reason:"]):
            key, _, val = line.partition(":")
            strength_class = ""
            if "Case strength" in key:
                val_lower = val.lower()
                if "strong" in val_lower:   strength_class = "strength-strong"
                elif "moderate" in val_lower: strength_class = "strength-moderate"
                elif "weak" in val_lower:     strength_class = "strength-weak"

            st.markdown(f"""
            <div style="display:flex;gap:0.5rem;margin:0.3rem 0;align-items:baseline;">
                <span style="color:#64748b;font-size:0.85rem;min-width:110px;">{key.strip()}:</span>
                <span class="{strength_class}" style="font-size:0.9rem;">{val.strip()}</span>
            </div>
            """, unsafe_allow_html=True)

    # Sections badge display
    if sections:
        st.markdown("**Applicable sections:**")
        badges = " ".join(f'<span class="section-badge">{s}</span>' for s in sections)
        st.markdown(badges, unsafe_allow_html=True)

        # Verification
        if sections:
            for s in verified.get("verified", []):
                st.markdown(f'<span class="verified-cite">✓ {s} — verified in knowledge base</span>', unsafe_allow_html=True)
            for s in verified.get("unverified", []):
                st.markdown(f'<span class="unverified-cite">⚠ {s} — not in knowledge base, verify manually</span>', unsafe_allow_html=True)

    st.markdown("---")

    # IRAC display
    if any(irac_parts.values()):
        st.markdown("**IRAC Analysis:**")
        for label, content in irac_parts.items():
            if content.strip():
                st.markdown(f"""
                <div class="irac-section">
                    <div class="irac-label">{label}</div>
                    <div style="font-size:0.9rem;margin-top:0.3rem;">{content.strip()}</div>
                </div>
                """, unsafe_allow_html=True)

    # Steps
    if steps:
        st.markdown("**What to do:**")
        for i, step in enumerate(steps, 1):
            st.markdown(f"{i}. {step}")

    st.markdown('</div>', unsafe_allow_html=True)


# ── PAGE ───────────────────────────────────────────────────────────────────────
col_chat, col_sidebar = st.columns([3, 1])

with col_sidebar:
    st.markdown("### About this tool")
    st.markdown("""
    Describe your legal problem and I'll:
    
    1. Ask follow-up questions to understand your case fully
    2. Give a complete legal judgement under BNS/BNSS/BSA 2023
    3. Show IRAC analysis (Issue → Rule → Application → Conclusion)
    4. Verify all cited sections
    5. Tell you case strength (Strong/Moderate/Weak)
    """)

    st.divider()

    if st.button("🔄 Start new case", type="secondary"):
        st.session_state.judge    = None
        st.session_state.messages = []
        st.session_state.started  = False
        st.session_state.done     = False
        st.rerun()

    st.divider()

    st.markdown("**Case types handled:**")
    st.markdown("""
    - Theft / snatching / robbery
    - Assault / physical violence
    - Cybercrime / online fraud / threats
    - Property disputes / landlord issues
    - Workplace / salary disputes
    - Domestic violence / dowry
    """)

with col_chat:
    st.title("⚖️ Case Chat")
    st.caption("Describe your legal problem. I'll ask questions then give a full legal judgement.")

    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 {msg["text"]}</div>', unsafe_allow_html=True)
        else:
            text = msg["text"]
            # Check if it's a judgement
            if "⚖️" in text or "Legal Assessment" in text or "Case strength" in text:
                parse_and_display_judgement(text)
            else:
                st.markdown(f'<div class="chat-bot">⚖️ {text}</div>', unsafe_allow_html=True)

    # Input
    if not st.session_state.done:
        placeholder = ("Describe your problem in detail (e.g. My employer has not paid my salary for 3 months...)"
                       if not st.session_state.started
                       else "Your answer...")

        user_input = st.chat_input(placeholder)

        if user_input:
            # Add user message to history
            st.session_state.messages.append({"role": "user", "text": user_input})

            # Get or create judge engine
            if st.session_state.judge is None:
                st.session_state.judge = JudgeEngine()

            # Get response
            with st.spinner("Analysing..."):
                if not st.session_state.started:
                    reply = st.session_state.judge.start(user_input)
                    st.session_state.started = True
                else:
                    reply = st.session_state.judge.reply(user_input)

            st.session_state.messages.append({"role": "bot", "text": reply})

            # Check if judgement was given
            if st.session_state.judge.has_judgement():
                st.session_state.done = True

            st.rerun()

    else:
        st.success("Judgement complete. Start a new case or upload evidence below.")

        # Evidence upload after judgement
        st.markdown("---")
        st.markdown("### 📸 Attach Evidence")
        st.caption("Upload a photo — I'll generate a BSA Section 63 certificate linked to this case.")

        evidence = st.file_uploader("Upload evidence photo", type=["jpg","jpeg","png"])
        if evidence:
            st.image(evidence, width=300)
            if st.button("Generate BSA Certificate", type="primary"):
                from m3_evidence.evidence import generate_evidence_certificate
                judge          = st.session_state.judge
                incident_brief = judge.get_summary() if judge else "Legal case via Nyaya-Setu"

                with st.spinner("Generating certificate..."):
                    cert, pdf_bytes = generate_evidence_certificate(
                        file_bytes=evidence.read(),
                        file_name=evidence.name,
                        complainant_name="Unknown",
                        incident_brief=incident_brief,
                    )

                st.success(f"Certificate generated: NS-{cert.certificate_id}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.code(cert.sha256_hash, language=None)
                    st.caption("SHA-256 hash — verify this against your original file")
                with col_b:
                    st.markdown(f"""
                    - **Device:** {cert.device_make} {cert.device_model}
                    - **GPS:** {cert.gps_coordinates}
                    - **Captured:** {cert.capture_timestamp}
                    - **Legal basis:** {cert.bsa_section}
                    """)

                st.download_button(
                    "⬇️ Download Certificate PDF",
                    data=pdf_bytes,
                    file_name=f"BSA_Certificate_NS-{cert.certificate_id}.pdf",
                    mime="application/pdf",
                )
