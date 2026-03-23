"""
Evidence Certificate Page
website/pages/4_evidence_cert.py

BSA Section 63 SHA-256 evidence certification
"""

import streamlit as st
import sys, os, io
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from m3_evidence.evidence import generate_evidence_certificate, verify_hash, compute_sha256

st.set_page_config(page_title="Evidence Certificate — Nyaya-Setu", page_icon="🔐", layout="wide")

st.markdown("""
<style>
.hash-display { font-family:monospace; font-size:0.85rem; background:#F0F4FF; padding:0.8rem; border-radius:8px; word-break:break-all; color:#1B3A6B; }
.cert-detail  { display:flex; gap:0.5rem; margin:0.3rem 0; }
.cert-label   { color:#64748b; font-size:0.85rem; min-width:130px; }
.cert-value   { color:#1e293b; font-size:0.85rem; font-weight:600; }
.verify-pass  { background:#E6F4EC; border:1px solid #1A6B3C; border-radius:8px; padding:1rem; }
.verify-fail  { background:#FDE8E8; border:1px solid #8B0000; border-radius:8px; padding:1rem; }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Evidence Certificate")
st.caption("Generate a BSA Section 63 compliant SHA-256 certificate for any digital evidence.")

# ── What is this ───────────────────────────────────────────────────────────────
with st.expander("ℹ️ What is a BSA Section 63 certificate?"):
    st.markdown("""
    **Bharatiya Sakshya Adhiniyam (BSA) 2023, Section 63** requires that electronic records
    submitted as court evidence must be accompanied by a certificate specifying:

    - The **SHA-256 hash value** of the electronic record (digital fingerprint)
    - The **device** used to capture or store the record
    - A statement that the record was produced in the ordinary course of activities

    **Why this matters:**
    - Without this certificate, photos, screenshots, and digital files may be inadmissible in court
    - The hash value proves the file has not been tampered with since the time of certification
    - Any modification to the original file after certification produces a different hash

    **Nyaya-Setu generates this certificate instantly** — no technical knowledge required.
    """)

tab_generate, tab_verify = st.tabs(["🔏 Generate Certificate", "🔍 Verify a File"])

# ── GENERATE ──────────────────────────────────────────────────────────────────
with tab_generate:
    col_upload, col_form = st.columns([1, 1])

    with col_upload:
        st.markdown("**Upload evidence file**")
        uploaded = st.file_uploader(
            "Upload photo or document",
            type=["jpg","jpeg","png","pdf","mp4","mov","docx"],
            label_visibility="collapsed",
        )
        if uploaded and uploaded.type.startswith("image"):
            st.image(uploaded, use_container_width=True)

    with col_form:
        st.markdown("**Case details (optional)**")
        complainant_name = st.text_input("Your name:", placeholder="e.g. Darshan Yadav")
        incident_brief   = st.text_area(
            "Brief description of incident:",
            height=100,
            placeholder="e.g. Phone snatched near Andheri Station on 22 March 2026 at 6 PM"
        )

    if uploaded and st.button("Generate BSA Certificate", type="primary"):
        file_bytes = uploaded.read()

        with st.spinner("Computing SHA-256 hash and extracting metadata..."):
            cert, pdf_bytes = generate_evidence_certificate(
                file_bytes=file_bytes,
                file_name=uploaded.name,
                complainant_name=complainant_name or "Unknown",
                incident_brief=incident_brief or "Evidence submitted via Nyaya-Setu",
            )

        st.success(f"✅ Certificate generated: NS-{cert.certificate_id}")
        st.markdown("---")

        # Main display
        col_hash, col_meta = st.columns([3, 2])

        with col_hash:
            st.markdown("**SHA-256 Hash (digital fingerprint):**")
            st.markdown(f'<div class="hash-display">{cert.sha256_hash}</div>', unsafe_allow_html=True)
            st.caption("If the hash of your file changes, the file has been tampered with.")

        with col_meta:
            st.markdown("**File details:**")
            details = [
                ("Certificate ID", f"NS-{cert.certificate_id}"),
                ("File name",      cert.file_name),
                ("File size",      f"{cert.file_size_bytes:,} bytes"),
                ("Dimensions",     f"{cert.image_width} × {cert.image_height} px" if cert.image_width != "0" else "N/A"),
                ("Device make",    cert.device_make),
                ("Device model",   cert.device_model),
                ("GPS",            cert.gps_coordinates),
                ("Captured",       cert.capture_timestamp),
                ("Certified on",   cert.certification_timestamp),
                ("Status",         cert.verification_status),
                ("Legal basis",    cert.bsa_section),
            ]
            for label, value in details:
                if value and value not in ["0", "0 × 0 px"]:
                    st.markdown(f"""
                    <div class="cert-detail">
                        <span class="cert-label">{label}:</span>
                        <span class="cert-value">{value}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")

        # Download
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Download Certificate PDF",
                data=pdf_bytes,
                file_name=f"BSA_Certificate_NS-{cert.certificate_id}.pdf",
                mime="application/pdf",
                type="primary",
            )
        with col_dl2:
            # Download hash as text file for easy verification
            hash_text = f"File: {cert.file_name}\nSHA-256: {cert.sha256_hash}\nCertified: {cert.certification_timestamp}\nCertificate ID: NS-{cert.certificate_id}\nLegal basis: {cert.bsa_section}"
            st.download_button(
                "⬇️ Download Hash File (.txt)",
                data=hash_text,
                file_name=f"hash_NS-{cert.certificate_id}.txt",
                mime="text/plain",
            )

        # Verification instructions
        st.markdown("---")
        st.markdown("**How to verify this certificate later:**")
        col_win, col_linux = st.columns(2)
        with col_win:
            st.markdown("**Windows:**")
            st.code(f'certutil -hashfile "{uploaded.name}" SHA256', language="powershell")
        with col_linux:
            st.markdown("**Linux / Mac:**")
            st.code(f'sha256sum "{uploaded.name}"', language="bash")
        st.caption("The output must exactly match the hash shown above.")


# ── VERIFY ────────────────────────────────────────────────────────────────────
with tab_verify:
    st.markdown("Upload the original file and enter the expected SHA-256 hash to verify integrity.")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        verify_file = st.file_uploader(
            "Upload file to verify",
            type=["jpg","jpeg","png","pdf","mp4","mov","docx"],
            key="verify_upload",
            label_visibility="collapsed",
        )
    with col_v2:
        expected_hash = st.text_input(
            "Expected SHA-256 hash:",
            placeholder="Paste the hash from the certificate...",
        )

    if verify_file and expected_hash and st.button("Verify Integrity", type="primary"):
        file_bytes = verify_file.read()
        actual     = compute_sha256(file_bytes)
        expected   = expected_hash.strip().lower()
        matches    = actual == expected

        if matches:
            st.markdown(f"""
            <div class="verify-pass">
                <h3 style="color:#1A6B3C;margin:0;">✅ INTEGRITY VERIFIED</h3>
                <p style="color:#1A6B3C;margin:0.5rem 0 0;">The file is authentic and has not been tampered with.</p>
                <div style="font-family:monospace;font-size:0.8rem;margin-top:0.8rem;color:#1A6B3C;">
                    Hash: {actual}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="verify-fail">
                <h3 style="color:#8B0000;margin:0;">❌ INTEGRITY FAILED</h3>
                <p style="color:#8B0000;margin:0.5rem 0 0;">Hash mismatch — file may have been modified.</p>
                <div style="font-size:0.82rem;margin-top:0.8rem;">
                    <strong>Expected:</strong> <span style="font-family:monospace;color:#8B0000;">{expected[:32]}...</span><br/>
                    <strong>Actual:</strong>   <span style="font-family:monospace;color:#8B0000;">{actual[:32]}...</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
