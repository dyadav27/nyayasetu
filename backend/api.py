"""
api.py — FastAPI Backend for Nyaya-Setu Website
Nyaya-Setu | Team IKS | SPIT CSE 2025-26
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, time, uuid, random, string
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

from document_analyzer import analyze_document, DocumentRAG, fetch_case_laws
from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
)
from modules.m3_evidence.evidence import generate_evidence_certificate
from legal_translator import translate_legal_text, translate_fir, get_supported_languages

load_dotenv()

# ── Twilio config ─────────────────────────────────────────────────────────────
TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WA_NUM = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

app = FastAPI(
    title="Nyaya-Setu API",
    description="AI-Powered Indian Legal Document Analyzer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores ──────────────────────────────────────────────────────────
doc_sessions: dict = {}   # session_id → {analysis, rag, doc_type, created_at}
otp_store:    dict = {}   # "+91XXXXXXXXXX" → {otp, expires_at, verified, attempts}


def cleanup_old_sessions():
    now = time.time()
    expired = [k for k, v in doc_sessions.items() if now - v["created_at"] > 3600]
    for k in expired:
        del doc_sessions[k]


def normalise_phone(phone: str) -> str:
    """Normalise to E.164 format, defaulting to India (+91)."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if not p.startswith("+"):
        p = "+91" + p.lstrip("0")
    return p


# ── Request / Response models ─────────────────────────────────────────────────
class QARequest(BaseModel):
    session_id: str
    question:   str

class ComplianceRequest(BaseModel):
    text: str

class CaseLawRequest(BaseModel):
    query:    str
    doc_type: str = "Legal Document"

class OTPSendRequest(BaseModel):
    phone: str

class OTPVerifyRequest(BaseModel):
    phone: str
    otp:   str

class TranslateRequest(BaseModel):
    text:          str
    source_lang:   str = "auto"
    target_lang:   str = "en"
    document_type: str = "FIR / Police Complaint"


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status":   "ok",
        "service":  "nyayasetu-api",
        "version":  "1.0.0",
        "sessions": len(doc_sessions),
    }


# ── Document analysis ─────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze(
    file:          UploadFile = File(...),
    type_override: str        = Form(default=None),
):
    cleanup_old_sessions()
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size: 10 MB")
    try:
        analysis, doc_rag = analyze_document(
            file_bytes,
            file.filename,
            type_override=type_override or None,
        )
        session_id = str(uuid.uuid4())
        doc_sessions[session_id] = {
            "analysis":   analysis,
            "rag":        doc_rag,
            "doc_type":   analysis.document_type,
            "created_at": time.time(),
        }
        result = analysis.model_dump()
        result["session_id"] = session_id
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


# ── Q&A ───────────────────────────────────────────────────────────────────────
@app.post("/api/qa")
async def question_answer(req: QARequest):
    """Answer questions about an analyzed document using RAG."""
    print(f"[QA] Received request for session: {req.session_id}")
    print(f"[QA] Question: {req.question[:100]}...")

    if not req.session_id:
        raise HTTPException(400, "session_id is required")

    session = doc_sessions.get(req.session_id)
    if not session:
        print(f"[QA] Session not found: {req.session_id}")
        raise HTTPException(404, f"Session not found or expired. Available sessions: {len(doc_sessions)}")

    if "rag" not in session:
        raise HTTPException(500, "RAG engine not initialized for this session")

    if not session["rag"]:
        raise HTTPException(500, "RAG engine not properly initialized")

    try:
        if not req.question or not req.question.strip():
            raise HTTPException(400, "Question cannot be empty")

        response = session["rag"].answer(req.question.strip())
        print(f"[QA] Answer generated with confidence: {response.confidence}")
        return JSONResponse(response.model_dump())

    except Exception as e:
        print(f"[QA ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Q&A failed: {str(e)}")


# ── Legal Translation ─────────────────────────────────────────────────────────
@app.post("/api/translate")
async def translate_document(req: TranslateRequest):
    """Translate legal documents (FIRs, complaints) between Indian languages
    with legal terminology preservation."""
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    if len(req.text) > 50000:
        raise HTTPException(400, "Text too long. Maximum 50,000 characters.")
    try:
        result = translate_legal_text(
            text=req.text.strip(),
            source_lang=req.source_lang if req.source_lang != "auto" else None,
            target_lang=req.target_lang,
            document_type=req.document_type,
        )
        if result.get("error"):
            raise HTTPException(500, f"Translation failed: {result['error']}")
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e}")
        raise HTTPException(500, f"Translation failed: {str(e)}")


@app.post("/api/translate/file")
async def translate_file(file: UploadFile = File(...), target_lang: str = Form(default="en")):
    """Upload a PDF/image FIR in regional language and get English translation."""
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size: 10 MB")
    try:
        from document_analyzer import extract_text
        text = extract_text(file_bytes, file.filename)
        if not text:
            raise HTTPException(400, "Could not extract text from file. Try a clearer scan.")
        result = translate_legal_text(
            text=text.strip(),
            source_lang=None,
            target_lang=target_lang,
            document_type="FIR / Police Complaint",
        )
        result["original_text"] = text
        result["filename"] = file.filename
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TRANSLATE FILE ERROR] {e}")
        raise HTTPException(500, f"Translation failed: {str(e)}")


@app.get("/api/translate/languages")
def list_languages():
    """List supported languages for translation."""
    return JSONResponse({"languages": get_supported_languages()})


# ── Compliance ────────────────────────────────────────────────────────────────
@app.post("/api/compliance")
async def compliance_check(req: ComplianceRequest):
    """Enhanced compliance check with RAG-based mapping"""
    try:
        result = compute_compliance_score(req.text, use_ai=True)
        message = generate_migration_message(result)
        return JSONResponse({
            "score":            result["score"],
            "grade":            result["grade"],
            "note":             result["note"],
            "message":          message,
            "mappings":         result["report"]["mappings"],
            "obsolete":         result["report"]["obsolete"],
            "total_references": result["report"]["total_old_references"],
            "ai_assisted":      result.get("ai_assisted", False),
            "timestamp":        result.get("timestamp", ""),
        })
    except Exception as e:
        print(f"[Compliance Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Compliance check failed: {str(e)}")


@app.post("/api/compliance/upload")
async def compliance_upload(file: UploadFile = File(...)):
    """Compliance check for uploaded PDF"""
    try:
        file_bytes = await file.read()
        text = extract_text_from_pdf_bytes(file_bytes)
        if text.startswith("ERROR"):
            raise HTTPException(400, text)
        result = compute_compliance_score(text, use_ai=True)
        message = generate_migration_message(result)
        return JSONResponse({
            "score":            result["score"],
            "grade":            result["grade"],
            "note":             result["note"],
            "message":          message,
            "mappings":         result["report"]["mappings"],
            "obsolete":         result["report"]["obsolete"],
            "total_references": result["report"]["total_old_references"],
            "ai_assisted":      result.get("ai_assisted", False),
            "timestamp":        result.get("timestamp", ""),
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Compliance Upload Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Compliance check failed: {str(e)}")


# ── Case laws ─────────────────────────────────────────────────────────────────
@app.post("/api/caselaws")
async def get_case_laws(req: CaseLawRequest):
    results = fetch_case_laws(req.query, req.doc_type)
    return JSONResponse({"results": results})


# ── OTP: Send via WhatsApp ────────────────────────────────────────────────────
@app.post("/api/otp/send")
async def send_otp(req: OTPSendRequest):
    """Send a 6-digit OTP to the complainant's phone via Twilio WhatsApp."""
    phone = normalise_phone(req.phone)

    existing = otp_store.get(phone)
    if existing and time.time() < existing.get("expires_at", 0) - 540:
        raise HTTPException(429, "OTP already sent. Please wait 60 seconds before requesting again.")

    otp = "".join(random.choices(string.digits, k=6))
    otp_store[phone] = {
        "otp":        otp,
        "expires_at": time.time() + 600,
        "verified":   False,
        "attempts":   0,
    }

    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=TWILIO_WA_NUM,
            to=f"whatsapp:{phone}",
            body=(
                f"🔐 *NyayaSetu — Phone Verification*\n\n"
                f"Your OTP for Evidence Certificate generation is:\n\n"
                f"*{otp}*\n\n"
                f"This OTP is valid for *10 minutes*.\n"
                f"Do not share this with anyone.\n\n"
                f"_NyayaSetu · Bridge to Justice_"
            ),
        )
        print(f"[OTP] Sent to {phone}")
        return JSONResponse({
            "success":    True,
            "message":    f"OTP sent to WhatsApp {phone}",
            "expires_in": 600,
        })
    except Exception as e:
        otp_store.pop(phone, None)
        print(f"[OTP ERROR] {e}")
        raise HTTPException(500, f"Failed to send OTP via WhatsApp: {str(e)}")


# ── OTP: Verify ───────────────────────────────────────────────────────────────
@app.post("/api/otp/verify")
async def verify_otp(req: OTPVerifyRequest):
    """Verify the OTP entered by the user."""
    phone  = normalise_phone(req.phone)
    record = otp_store.get(phone)

    if not record:
        raise HTTPException(400, "No OTP found for this number. Please request a new one.")

    if time.time() > record["expires_at"]:
        otp_store.pop(phone, None)
        raise HTTPException(400, "OTP has expired. Please request a new one.")

    record["attempts"] += 1
    if record["attempts"] > 5:
        otp_store.pop(phone, None)
        raise HTTPException(429, "Too many incorrect attempts. Please request a new OTP.")

    if req.otp.strip() != record["otp"]:
        remaining = 5 - record["attempts"]
        raise HTTPException(400, f"Incorrect OTP. {remaining} attempt(s) remaining.")

    record["verified"] = True
    print(f"[OTP] Verified: {phone}")
    return JSONResponse({"success": True, "verified": True, "phone": phone})


# ── Evidence certificate ──────────────────────────────────────────────────────
@app.post("/api/evidence")
async def evidence_certificate(
    file:                UploadFile = File(...),
    complainant_name:    str = Form(default="Not provided"),
    complainant_phone:   str = Form(default=""),
    complainant_address: str = Form(default=""),
    incident_brief:      str = Form(default="Evidence submitted via NyayaSetu"),
    incident_date:       str = Form(default=""),
    police_station:      str = Form(default=""),
):
    """
    Generate BSA Section 63 SHA-256 evidence certificate.
    Phone number must be OTP-verified before calling this endpoint.
    """
    if complainant_phone:
        phone  = normalise_phone(complainant_phone)
        record = otp_store.get(phone)
        if not record or not record.get("verified"):
            raise HTTPException(403, "Phone number not verified. Please complete OTP verification.")

    file_bytes = await file.read()

    try:
        cert, pdf_bytes = generate_evidence_certificate(
            file_bytes          = file_bytes,
            file_name           = file.filename,
            complainant_name    = complainant_name,
            complainant_phone   = complainant_phone,
            complainant_address = complainant_address,
            incident_brief      = incident_brief,
            incident_date       = incident_date,
            police_station      = police_station,
        )
    except Exception as e:
        print(f"[EVIDENCE ERROR] {e}")
        raise HTTPException(500, f"Certificate generation failed: {str(e)}")

    # Save PDF
    os.makedirs("temp_media", exist_ok=True)
    pdf_name = f"BSA_Certificate_NS-{cert.certificate_id}.pdf"
    pdf_path = os.path.join("temp_media", pdf_name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Clear OTP after successful certificate generation
    if complainant_phone:
        otp_store.pop(normalise_phone(complainant_phone), None)

    return JSONResponse({
        "certificate_id":          cert.certificate_id,
        "sha256_hash":             cert.sha256_hash,
        "file_name":               cert.file_name,
        "file_size_bytes":         cert.file_size_bytes,
        "complainant_name":        cert.complainant_name,
        "complainant_phone":       cert.complainant_phone,
        "complainant_address":     cert.complainant_address,
        "incident_brief":          cert.incident_brief,
        "incident_date":           cert.incident_date,
        "police_station":          cert.police_station,
        "capture_timestamp":       cert.capture_timestamp,
        "certification_timestamp": cert.certification_timestamp,
        "device_make":             cert.device_make,
        "device_model":            cert.device_model,
        "gps_coordinates":         cert.gps_coordinates,
        "image_width":             cert.image_width,
        "image_height":            cert.image_height,
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