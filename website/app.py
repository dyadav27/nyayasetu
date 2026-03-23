"""
Nyaya-Setu Website — Main App
website/app.py

Run: streamlit run website/app.py
"""

import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(
    page_title="Nyaya-Setu — Bridge to Justice",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background: #1B3A6B; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: #D6E4F7 !important; }

    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #1B3A6B 0%, #2E5FA3 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2.2rem; }
    .main-header p  { color: #D6E4F7; margin: 0.5rem 0 0; font-size: 1.1rem; }

    /* Feature cards */
    .feature-card {
        background: #F8F9FC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s;
    }
    .feature-card:hover { box-shadow: 0 4px 16px rgba(27,58,107,0.12); }
    .feature-card h3 { color: #1B3A6B; margin: 0 0 0.5rem; }
    .feature-card p  { color: #64748b; margin: 0; font-size: 0.9rem; }

    /* Risk badges */
    .badge-safe     { background:#E6F4EC; color:#1A6B3C; padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }
    .badge-caution  { background:#FFF8E7; color:#C8960C; padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }
    .badge-high     { background:#FDE8E8; color:#8B0000; padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }
    .badge-illegal  { background:#1B3A6B; color:#ffffff; padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; }

    /* Confidence bar */
    .conf-high   { color: #1A6B3C; font-weight: 600; }
    .conf-medium { color: #C8960C; font-weight: 600; }
    .conf-low    { color: #8B0000; font-weight: 600; }

    /* IRAC box */
    .irac-box {
        background: #F0F4FF;
        border-left: 4px solid #2E5FA3;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }
    .irac-label { color: #1B3A6B; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .irac-text  { color: #1e293b; margin-top: 0.3rem; }

    /* Chat bubble */
    .chat-user { background:#E8F0FB; border-radius:12px 12px 2px 12px; padding:0.8rem 1rem; margin:0.5rem 0; color:#1B3A6B; }
    .chat-bot  { background:#F8F9FC; border:1px solid #E2E8F0; border-radius:12px 12px 12px 2px; padding:0.8rem 1rem; margin:0.5rem 0; }

    /* Hide default streamlit branding */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Home page ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚖️ Nyaya-Setu</h1>
    <p>Bridge to Justice — AI-powered Indian legal assistant under BNS 2023, BNSS 2023 &amp; BSA 2023</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>📄 Document Analyzer</h3>
        <p>Upload rental agreements, employment contracts, legal notices. Get clause-by-clause risk analysis, plain-language explanations, and relevant case law.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card">
        <h3>🔄 Compliance Checker</h3>
        <p>Check if your legal document uses obsolete IPC/CrPC sections. Get instant BNS/BNSS equivalents and a 0–100 compliance score.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>⚖️ Case Chat</h3>
        <p>Describe your legal problem. The AI asks follow-up questions, then gives a full IRAC judgement with applicable BNS sections, punishment range, and case strength.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card">
        <h3>🔐 Evidence Certificate</h3>
        <p>Upload a photo as evidence. Get a SHA-256 cryptographic certificate compliant with BSA Section 63 — court-admissible chain of custody documentation.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

st.markdown("### How it works")
cols = st.columns(4)
steps = [
    ("1", "Upload or describe", "Upload a document or describe your legal problem in plain language."),
    ("2", "AI analyses", "Llama-3 analyses under BNS 2023, BNSS 2023, BSA 2023 — grounded in verified law, not hallucinations."),
    ("3", "Get judgement", "Receive a full legal assessment with IRAC reasoning, applicable sections, and case strength."),
    ("4", "Certify evidence", "Upload photos as evidence — get a BSA-compliant SHA-256 certificate instantly."),
]
for col, (num, title, desc) in zip(cols, steps):
    with col:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem;">
            <div style="background:#1B3A6B; color:white; width:36px; height:36px; border-radius:50%;
                        display:inline-flex; align-items:center; justify-content:center;
                        font-weight:700; font-size:1.1rem; margin-bottom:0.8rem;">{num}</div>
            <h4 style="color:#1B3A6B; margin:0 0 0.4rem;">{title}</h4>
            <p style="color:#64748b; font-size:0.85rem; margin:0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.caption("⚠️ Nyaya-Setu provides legal guidance, not legal advice. For court proceedings, always consult a qualified advocate.")
st.caption("Built by Team IKS | K J Somaiya School of Engineering | CSE Dept | AY 2025-26")
