"""
Document Analyzer Page
website/pages/1_document_analyzer.py

Features:
- PDF / image / text upload
- Clause-by-clause risk analysis (Safe / Caution / High Risk / Illegal)
- RAG Q&A over the uploaded document
- IndianKanoon case law retrieval
- Confidence scoring on every answer
"""

import streamlit as st
import sys, os, io, json, re, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import ollama
import fitz          # PyMuPDF
import requests
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Document Analyzer — Nyaya-Setu", page_icon="📄", layout="wide")

OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", "llama3")
INDIANKANOON_KEY   = os.getenv("INDIANKANOON_API_KEY", "")
CHROMA_DIR         = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chromadb")

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.risk-safe    { background:#E6F4EC; border-left:4px solid #1A6B3C; padding:0.8rem 1rem; border-radius:0 8px 8px 0; margin:0.5rem 0; }
.risk-caution { background:#FFF8E7; border-left:4px solid #C8960C; padding:0.8rem 1rem; border-radius:0 8px 8px 0; margin:0.5rem 0; }
.risk-high    { background:#FDE8E8; border-left:4px solid #8B0000; padding:0.8rem 1rem; border-radius:0 8px 8px 0; margin:0.5rem 0; }
.risk-illegal { background:#1B3A6B; border-left:4px solid #0a2040; padding:0.8rem 1rem; border-radius:0 8px 8px 0; margin:0.5rem 0; color:white; }
.risk-label { font-weight:700; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem; }
.conf-score { font-size:0.8rem; font-weight:600; }
.caselaw-card { background:#F0F4FF; border:1px solid #C7D8F5; border-radius:8px; padding:1rem; margin:0.5rem 0; }
</style>
""", unsafe_allow_html=True)


# ── PDF extraction ─────────────────────────────────────────────────────────────
def extract_text_pdf(file_bytes: bytes) -> str:
    doc   = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [page.get_text("text") for page in doc]
    doc.close()
    return "\n\n".join(pages).strip()

def extract_text_image(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        img  = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img).strip()
    except ImportError:
        return "OCR not available — please upload a PDF or paste text directly."

def segment_clauses(text: str) -> list[str]:
    """Split document into clauses using sentence boundaries + numbering patterns."""
    # Split on numbered clauses, lettered sub-clauses, and double newlines
    splits = re.split(
        r'\n(?=\d+[\.\)]\s|\([a-z]\)\s|Clause\s|Section\s|Article\s)|(?<=[.;])\s*\n\s*\n',
        text
    )
    # Filter: keep chunks between 30 and 800 chars
    clauses = [c.strip() for c in splits if 30 < len(c.strip()) < 800]
    return clauses[:40]  # max 40 clauses to avoid token overflow


# ── Risk analysis ─────────────────────────────────────────────────────────────
RISK_LABELS = ["Safe", "Caution", "High Risk", "Illegal"]

def analyse_clauses(clauses: list[str]) -> list[dict]:
    """Send clauses to Llama-3 for risk classification."""
    results = []
    for i, clause in enumerate(clauses):
        prompt = f"""You are an expert Indian legal analyst.
Classify this clause from an Indian legal document into exactly ONE category:
- Safe: fair, balanced, standard clause
- Caution: one-sided but not illegal; user should negotiate
- High Risk: significantly unfair; could harm the user legally or financially
- Illegal: violates Indian law (Consumer Protection Act, Contract Act, Rent Control, etc.)

After the label, give a ONE sentence plain-English explanation of why.
Then give a confidence score 0.0–1.0.

CLAUSE: {clause[:400]}

Respond ONLY in this exact JSON format:
{{"label": "Safe|Caution|High Risk|Illegal", "reason": "one sentence", "confidence": 0.85}}"""

        try:
            resp = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0, "num_ctx": 1024, "num_gpu": 99},
            )
            raw = resp["message"]["content"].strip()
            raw = re.sub(r"```json\s*|```\s*", "", raw).strip()
            data = json.loads(raw)
            results.append({
                "clause":     clause,
                "label":      data.get("label", "Safe"),
                "reason":     data.get("reason", ""),
                "confidence": float(data.get("confidence", 0.7)),
                "index":      i + 1,
            })
        except Exception as e:
            results.append({
                "clause":     clause,
                "label":      "Caution",
                "reason":     "Could not analyse — review manually.",
                "confidence": 0.3,
                "index":      i + 1,
            })
    return results


# ── Confidence layer ──────────────────────────────────────────────────────────
def confidence_label(score: float) -> tuple[str, str]:
    """Return (text, css_class) based on confidence score."""
    if score >= 0.75:
        return f"High confidence ({score:.0%})", "conf-high"
    elif score >= 0.40:
        return f"Medium confidence ({score:.0%}) — verify with a lawyer", "conf-medium"
    else:
        return f"Low confidence ({score:.0%}) — consult a qualified advocate", "conf-low"


# ── RAG Q&A over document ─────────────────────────────────────────────────────
def answer_question(question: str, doc_text: str) -> dict:
    """Answer a question grounded in the uploaded document text."""
    # Simple retrieval: find most relevant 800-char chunk
    chunks = [doc_text[i:i+800] for i in range(0, min(len(doc_text), 6000), 600)]

    # Score chunks by keyword overlap
    q_words = set(question.lower().split())
    best_chunk = max(chunks, key=lambda c: len(q_words & set(c.lower().split())))

    prompt = f"""You are an Indian legal assistant. A user has uploaded a legal document and asked a question.
Answer ONLY based on the document excerpt below. Do NOT use outside knowledge.
If the answer is not in the document, say "This information is not in the document."
Give a confidence score 0.0–1.0 based on how clearly the document answers the question.

DOCUMENT EXCERPT:
{best_chunk}

QUESTION: {question}

Respond ONLY in this JSON format:
{{"answer": "...", "confidence": 0.85, "source_quote": "short quote from document that supports answer"}}"""

    try:
        resp = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_ctx": 2048, "num_gpu": 99},
        )
        raw  = re.sub(r"```json\s*|```\s*", "", resp["message"]["content"]).strip()
        data = json.loads(raw)
        return data
    except Exception:
        return {"answer": "Could not process question.", "confidence": 0.0, "source_quote": ""}


# ── IndianKanoon case law ─────────────────────────────────────────────────────
def fetch_case_law(query: str) -> list[dict]:
    """Fetch relevant case law from IndianKanoon API."""
    if not INDIANKANOON_KEY:
        # Return demo result if no API key
        return [{
            "title":   "IndianKanoon API key not configured",
            "doc_id":  "",
            "summary": "Add INDIANKANOON_API_KEY to your .env file. Get a free key at indiankanoon.org/api/",
            "url":     "https://indiankanoon.org",
        }]
    try:
        resp = requests.get(
            "https://api.indiankanoon.org/search/",
            params={"formInput": query, "pagenum": 0},
            headers={"Authorization": f"Token {INDIANKANOON_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for doc in data.get("docs", [])[:3]:
            results.append({
                "title":   doc.get("title", "Untitled"),
                "doc_id":  doc.get("tid", ""),
                "summary": doc.get("headline", "No summary available.")[:300],
                "url":     f"https://indiankanoon.org/doc/{doc.get('tid', '')}",
            })
        return results
    except Exception as e:
        return [{"title": f"Error: {e}", "doc_id": "", "summary": "", "url": ""}]


def summarise_case(case_text: str) -> str:
    """Summarise a case judgment into 2-3 plain sentences."""
    prompt = f"""Summarise this Indian court judgment in 2-3 plain English sentences.
Focus on: what the case was about, what the court decided, and why it matters.

JUDGMENT EXCERPT: {case_text[:600]}

Respond with just the summary, nothing else."""
    try:
        resp = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_ctx": 1024, "num_gpu": 99},
        )
        return resp["message"]["content"].strip()
    except Exception:
        return case_text[:200]


# ── Compliance score ──────────────────────────────────────────────────────────
def quick_compliance(text: str) -> dict:
    """Run IPC→BNS compliance check from lex_validator."""
    try:
        from lex_validator import compute_compliance_score
        return compute_compliance_score(text)
    except Exception:
        return {"score": -1, "grade": "?", "note": "Compliance check unavailable."}


# ═══════════════════════════════════════════════════════════════════════════════
# ── PAGE UI ────────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

st.title("📄 Document Analyzer")
st.caption("Upload any Indian legal document — rental agreement, employment contract, legal notice, court summons.")

# ── Upload ─────────────────────────────────────────────────────────────────────
col_upload, col_info = st.columns([2, 1])

with col_upload:
    upload_mode = st.radio("Input method", ["Upload PDF", "Upload Image", "Paste text"], horizontal=True)

    doc_text = ""

    if upload_mode == "Upload PDF":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            with st.spinner("Extracting text..."):
                doc_text = extract_text_pdf(uploaded.read())
            st.success(f"Extracted {len(doc_text):,} characters from PDF")

    elif upload_mode == "Upload Image":
        uploaded = st.file_uploader("Upload image", type=["jpg","jpeg","png"], label_visibility="collapsed")
        if uploaded:
            st.image(uploaded, width=400)
            with st.spinner("Running OCR..."):
                doc_text = extract_text_image(uploaded.read())
            if doc_text:
                st.success(f"OCR extracted {len(doc_text):,} characters")

    else:
        doc_text = st.text_area("Paste document text here", height=200,
                                placeholder="Paste the text of any legal document...")

with col_info:
    st.markdown("""
    **Supported documents:**
    - Rental / lease agreements
    - Employment contracts
    - Loan agreements
    - Legal notices
    - Court summons
    - FIRs and charge sheets
    - Vendor / service agreements
    """)

# ── Analysis ───────────────────────────────────────────────────────────────────
if doc_text and len(doc_text.strip()) > 50:

    # Store in session state
    if "doc_text" not in st.session_state or st.session_state.doc_text != doc_text:
        st.session_state.doc_text      = doc_text
        st.session_state.clauses       = None
        st.session_state.analysis      = None
        st.session_state.qa_history    = []

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Clause Risk Analysis",
        "💬 Ask Questions (RAG)",
        "📚 Case Law",
        "✅ Compliance Score",
    ])

    # ── TAB 1: Clause Risk ─────────────────────────────────────────────────────
    with tab1:
        if st.button("Analyse all clauses", type="primary", key="analyse_btn"):
            with st.spinner("Segmenting clauses..."):
                st.session_state.clauses = segment_clauses(doc_text)

            progress = st.progress(0, text="Analysing clauses with Llama-3 on GPU...")
            results  = []
            for i, clause in enumerate(st.session_state.clauses):
                results.extend(analyse_clauses([clause]))
                progress.progress((i+1)/len(st.session_state.clauses),
                                  text=f"Analysing clause {i+1}/{len(st.session_state.clauses)}...")
            st.session_state.analysis = results
            progress.empty()

        if st.session_state.get("analysis"):
            analysis = st.session_state.analysis

            # Summary stats
            counts = {l: sum(1 for a in analysis if a["label"]==l) for l in RISK_LABELS}
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("✅ Safe",      counts["Safe"])
            c2.metric("⚠️ Caution",   counts["Caution"])
            c3.metric("🔴 High Risk", counts["High Risk"])
            c4.metric("🚫 Illegal",   counts["Illegal"])

            st.markdown("---")

            # Filter
            filter_label = st.selectbox("Show clauses:", ["All"] + RISK_LABELS)
            filtered = [a for a in analysis if filter_label=="All" or a["label"]==filter_label]

            for item in filtered:
                label     = item["label"]
                css_class = {"Safe":"risk-safe","Caution":"risk-caution",
                             "High Risk":"risk-high","Illegal":"risk-illegal"}.get(label,"risk-safe")
                conf_text, conf_css = confidence_label(item["confidence"])

                color_map = {"Safe":"#1A6B3C","Caution":"#C8960C","High Risk":"#8B0000","Illegal":"#ffffff"}
                label_color = color_map.get(label, "#1A6B3C")

                st.markdown(f"""
                <div class="{css_class}">
                    <div class="risk-label" style="color:{label_color};">
                        Clause {item['index']} — {label}
                    </div>
                    <div style="font-size:0.9rem; margin:0.3rem 0;">{item['clause'][:300]}...</div>
                    <div style="font-size:0.85rem; margin-top:0.4rem; opacity:0.85;">
                        <strong>Why:</strong> {item['reason']}
                    </div>
                    <div class="conf-score {conf_css}" style="margin-top:0.3rem; font-size:0.78rem;">
                        {conf_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 2: RAG Q&A ─────────────────────────────────────────────────────────
    with tab2:
        st.markdown("Ask any question about the uploaded document.")

        # Chat history
        for msg in st.session_state.get("qa_history", []):
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">🧑 {msg["text"]}</div>', unsafe_allow_html=True)
            else:
                conf_text, conf_css = confidence_label(msg.get("confidence", 0.5))
                st.markdown(f"""
                <div class="chat-bot">
                    <div>⚖️ {msg["text"]}</div>
                    {"<div style='font-size:0.8rem;color:#64748b;margin-top:0.5rem;'><em>Source: \"" + msg.get("quote","") + "\"</em></div>" if msg.get("quote") else ""}
                    <div class="conf-score {conf_css}" style="margin-top:0.4rem; font-size:0.78rem;">{conf_text}</div>
                </div>
                """, unsafe_allow_html=True)

        question = st.chat_input("Ask about this document...")
        if question:
            st.session_state.qa_history.append({"role": "user", "text": question})
            with st.spinner("Searching document..."):
                answer = answer_question(question, doc_text)
            st.session_state.qa_history.append({
                "role":       "bot",
                "text":       answer["answer"],
                "confidence": answer["confidence"],
                "quote":      answer.get("source_quote", ""),
            })
            st.rerun()

    # ── TAB 3: Case Law ────────────────────────────────────────────────────────
    with tab3:
        st.markdown("Find relevant Indian court judgments for your document type.")

        query = st.text_input("Search case law:",
            placeholder="e.g. landlord eviction without notice Mumbai")
        if st.button("Search IndianKanoon", key="caselaw_btn") and query:
            with st.spinner("Fetching case law..."):
                cases = fetch_case_law(query)
            for case in cases:
                st.markdown(f"""
                <div class="caselaw-card">
                    <strong>{case['title']}</strong><br/>
                    <span style="font-size:0.85rem; color:#475569;">{case['summary']}</span><br/>
                    {"<a href='" + case['url'] + "' target='_blank' style='font-size:0.8rem;color:#1B3A6B;'>View on IndianKanoon →</a>" if case.get('url') else ""}
                </div>
                """, unsafe_allow_html=True)

        # Auto-suggest query based on doc content
        if st.button("Auto-suggest query from document", key="auto_query"):
            with st.spinner("Generating search query..."):
                prompt = f"Based on this legal document, generate a 5-7 word Indian court case search query.\nDocument excerpt: {doc_text[:400]}\nRespond with ONLY the search query, nothing else."
                resp   = ollama.chat(model=OLLAMA_MODEL, messages=[{"role":"user","content":prompt}],
                                     options={"temperature":0.2,"num_gpu":99})
                suggested = resp["message"]["content"].strip()
            st.info(f"Suggested query: **{suggested}**")

    # ── TAB 4: Compliance ──────────────────────────────────────────────────────
    with tab4:
        st.markdown("Check if this document uses obsolete IPC/CrPC references instead of BNS/BNSS.")

        if st.button("Run compliance check", key="comp_btn"):
            with st.spinner("Scanning for IPC/CrPC references..."):
                result = quick_compliance(doc_text)

            if result["score"] == -1:
                st.error(result["note"])
            else:
                score = result["score"]
                grade = result["grade"]

                # Score display
                col_s, col_g = st.columns([3, 1])
                with col_s:
                    st.metric("BNS Compliance Score", f"{score}/100")
                    st.progress(score / 100)
                with col_g:
                    grade_colors = {"A":"#1A6B3C","B":"#2E5FA3","C":"#C8960C","F":"#8B0000"}
                    st.markdown(f"""
                    <div style="text-align:center; padding:1rem; background:{grade_colors.get(grade,'#64748b')};
                                color:white; border-radius:8px; font-size:2rem; font-weight:700;">
                        {grade}
                    </div>
                    """, unsafe_allow_html=True)

                st.info(result["note"])

                # Mappings table
                mappings = result.get("report", {}).get("mappings", [])
                if mappings:
                    st.markdown("**IPC → BNS corrections required:**")
                    for m in mappings:
                        icon = "❌" if m["new"] == "ABOLISHED" else "✅"
                        st.markdown(f"{icon} `{m['old']}` → `{m['new']}` — {m['name']}")
