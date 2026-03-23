"""
api.py — FastAPI Backend for Nyaya-Setu Website
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Endpoints:
  POST /api/analyze          — Upload + analyze document
  POST /api/qa               — Ask question about analyzed document
  POST /api/compliance       — IPC→BNS compliance check
  GET  /api/caselaws         — Search Indian case laws
  GET  /api/health           — Health check

Run: uvicorn api:app --reload --port 8001
(WhatsApp bot runs on port 8000, website API on 8001)
"""

import os, sys, json, time, uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))
from document_analyzer import analyze_document, DocumentRAG, fetch_case_laws
from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
)
from m3_evidence.evidence import generate_evidence_certificate

load_dotenv()

app = FastAPI(
    title="Nyaya-Setu API",
    description="AI-Powered Indian Legal Document Analyzer",
    version="1.0.0",
)

# ── CORS — allow React frontend ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store for document RAG ──────────────────────────────────
# session_id → {analysis, rag, doc_type, created_at}
doc_sessions: dict = {}

def cleanup_old_sessions():
    """Remove sessions older than 1 hour."""
    now = time.time()
    expired = [k for k, v in doc_sessions.items() if now - v["created_at"] > 3600]
    for k in expired:
        del doc_sessions[k]


# ── Request/Response models ────────────────────────────────────────────────────
class QARequest(BaseModel):
    session_id: str
    question:   str

class ComplianceRequest(BaseModel):
    text: str

class CaseLawRequest(BaseModel):
    query:    str
    doc_type: str = "Legal Document"


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status":   "ok",
        "service":  "nyayasetu-api",
        "version":  "1.0.0",
        "sessions": len(doc_sessions),
    }


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Upload a PDF or image legal document.
    Returns full analysis: clauses, risk scores, summary, case laws.
    """
    cleanup_old_sessions()

    # Validate file type
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:   # 10 MB limit
        raise HTTPException(400, "File too large. Maximum size: 10 MB")

    try:
        # Run full analysis (this takes 30-60 seconds for a long document)
        analysis, doc_rag = analyze_document(file_bytes, file.filename)

        # Store session for follow-up Q&A
        session_id = str(uuid.uuid4())
        doc_sessions[session_id] = {
            "analysis":   analysis,
            "rag":        doc_rag,
            "doc_type":   analysis.document_type,
            "created_at": time.time(),
        }

        # Serialize to dict
        result = analysis.model_dump()
        result["session_id"] = session_id

        return JSONResponse(result)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.post("/api/qa")
async def question_answer(req: QARequest):
    """
    Ask a question about a previously analyzed document.
    Requires session_id from /api/analyze response.
    """
    session = doc_sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired. Please re-upload the document.")

    rag: DocumentRAG = session["rag"]
    doc_type: str    = session["doc_type"]

    response = rag.answer(req.question, doc_type)
    return JSONResponse(response.model_dump())


@app.post("/api/compliance")
async def compliance_check(req: ComplianceRequest):
    """
    Check IPC→BNS compliance of text.
    Returns score, grade, and migration mappings.
    """
    result  = compute_compliance_score(req.text)
    message = generate_migration_message(result)
    return JSONResponse({
        "score":    result["score"],
        "grade":    result["grade"],
        "note":     result["note"],
        "message":  message,
        "mappings": result["report"]["mappings"],
        "obsolete": result["report"]["obsolete"],
    })


@app.post("/api/compliance/upload")
async def compliance_upload(file: UploadFile = File(...)):
    """Upload a PDF and get compliance score."""
    file_bytes = await file.read()
    text       = extract_text_from_pdf_bytes(file_bytes)
    if text.startswith("ERROR"):
        raise HTTPException(400, text)
    result  = compute_compliance_score(text)
    message = generate_migration_message(result)
    return JSONResponse({
        "score":    result["score"],
        "grade":    result["grade"],
        "note":     result["note"],
        "message":  message,
        "mappings": result["report"]["mappings"],
    })


@app.post("/api/caselaws")
async def get_case_laws(req: CaseLawRequest):
    """Search Indian Kanoon for relevant case laws."""
    results = fetch_case_laws(req.query, req.doc_type)
    return JSONResponse({"results": results})


@app.post("/api/evidence")
async def evidence_certificate(
    file:             UploadFile = File(...),
    complainant_name: str        = Form("Unknown"),
    incident_brief:   str        = Form("Evidence submitted via Nyaya-Setu"),
):
    """
    Generate BSA Section 63 SHA-256 evidence certificate.
    Returns certificate data + PDF download URL.
    """
    file_bytes = await file.read()

    cert, pdf_bytes = generate_evidence_certificate(
        file_bytes=file_bytes,
        file_name=file.filename,
        complainant_name=complainant_name,
        incident_brief=incident_brief,
    )

    # Save PDF
    os.makedirs("temp_media", exist_ok=True)
    pdf_name = f"Certificate_NS-{cert.certificate_id}.pdf"
    pdf_path = os.path.join("temp_media", pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return JSONResponse({
        "certificate_id":          cert.certificate_id,
        "sha256_hash":             cert.sha256_hash,
        "file_name":               cert.file_name,
        "file_size_bytes":         cert.file_size_bytes,
        "capture_timestamp":       cert.capture_timestamp,
        "device_make":             cert.device_make,
        "device_model":            cert.device_model,
        "gps_coordinates":         cert.gps_coordinates,
        "verification_status":     cert.verification_status,
        "bsa_section":             cert.bsa_section,
        "pdf_download_url":        f"/api/media/{pdf_name}",
    })


@app.get("/api/media/{filename}")
def serve_media(filename: str):
    path = os.path.join("temp_media", filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(404, "File not found")


@app.get("/api/sessions")
def list_sessions():
    """Dev endpoint — list active sessions."""
    return {
        "count": len(doc_sessions),
        "sessions": [
            {
                "id":       k,
                "doc_type": v["doc_type"],
                "age_mins": round((time.time() - v["created_at"]) / 60, 1),
            }
            for k, v in doc_sessions.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
