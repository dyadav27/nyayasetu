"""
Nyaya-Setu — FastAPI Main Application (v5)
Full feature set: Judge Engine + Lex-Validator features
- Interactive case questioning
- IRAC reasoning
- Citation verification
- IPC→BNS migration checker
- Compliance scoring
- BSA Section 63 evidence certificate
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time, traceback
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
import requests
from judge_engine import get_judge, reset_judge
from modules.m3_evidence.evidence import generate_evidence_certificate
from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
    extract_text_from_image_bytes,
)

load_dotenv()

# ── Twilio ─────────────────────────────────────────────────────────────────────
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
NGROK_URL    = os.getenv("NGROK_URL", "http://localhost:8000")
twilio       = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

# ── Session store ──────────────────────────────────────────────────────────────
sessions: dict = {}

def get_session(phone: str) -> dict:
    if phone not in sessions:
        sessions[phone] = {
            "phone":   phone,
            "state":   "IDLE",   # IDLE, ACTIVE, AWAITING_EVIDENCE, DONE
            "mode":    "case",   # "case" or "compliance"
            "created": time.time(),
        }
    return sessions[phone]

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Nyaya-Setu", version="5.0.0")

# ── Twilio helpers ─────────────────────────────────────────────────────────────
def send_text(to: str, body: str):
    # Split long messages (WhatsApp limit ~4096 chars)
    if len(body) > 1500:
        parts = [body[i:i+1500] for i in range(0, len(body), 1500)]
        for part in parts:
            twilio.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{to}", body=part)
    else:
        twilio.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{to}", body=body)

def download_media(url: str) -> bytes:
    r = requests.get(url, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=30)
    r.raise_for_status()
    return r.content

def save_and_get_url(data: bytes, filename: str) -> str:
    os.makedirs("temp_media", exist_ok=True)
    with open(os.path.join("temp_media", filename), "wb") as f:
        f.write(data)
    return f"{NGROK_URL}/media/{filename}"

# ── Intent helpers ─────────────────────────────────────────────────────────────
GREETINGS    = {"hi","hello","namaste","start","help","hey","hii","helo"}
RESET_W      = {"reset","restart","new","clear","start over","quit"}
COMPLIANCE_W = {"check document","compliance","ipc","old fir","check fir",
                "check notice","migration","bns check","verify document"}

def is_greeting(t):    return t.lower().strip() in GREETINGS
def is_reset(t):       return any(w in t.lower() for w in RESET_W)
def wants_compliance(t): return any(w in t.lower() for w in COMPLIANCE_W)

# ── Webhook ────────────────────────────────────────────────────────────────────
@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form        = await request.form()
    from_number = str(form.get("From","")).replace("whatsapp:","")
    body        = str(form.get("Body","")).strip()
    num_media   = int(form.get("NumMedia", 0))
    media_url   = str(form.get("MediaUrl0",""))
    media_type  = str(form.get("MediaContentType0",""))
    session     = get_session(from_number)

    print(f"\n[MSG] {from_number[-4:]} | state={session['state']} | mode={session['mode']} | '{body[:60]}'")

    background_tasks.add_task(
        handle, from_number, body, num_media, media_url, media_type, session
    )
    return PlainTextResponse(str(MessagingResponse()), media_type="application/xml")


# ── Main handler ───────────────────────────────────────────────────────────────
async def handle(from_number, body, num_media, media_url, media_type, session):
    try:
        # Reset
        if is_reset(body):
            reset_judge(from_number)
            sessions[from_number] = get_session(from_number)
            send_text(from_number, "Conversation cleared. Send your complaint or type *check document* to verify a legal document.")
            return

        # Document upload (PDF) → compliance check
        if num_media > 0 and "pdf" in media_type:
            await handle_pdf(from_number, media_url, session)
            return

        # Image → could be evidence OR a photo of a document
        if num_media > 0 and "image" in media_type:
            await handle_image(from_number, media_url, media_type, session)
            return

        # Audio
        if num_media > 0 and "audio" in media_type:
            send_text(from_number, "Voice notes coming soon. Please type your complaint.")
            return

        # Compliance mode trigger
        if wants_compliance(body) and session["state"] == "IDLE":
            session["mode"]  = "compliance"
            session["state"] = "AWAITING_DOCUMENT"
            send_text(from_number,
                "📋 Document Compliance Checker\n\n"
                "Send me a PDF or photo of any legal document — FIR, court notice, petition, agreement.\n\n"
                "I will:\n"
                "• Check if it uses obsolete IPC sections\n"
                "• Show the correct BNS/BNSS equivalents\n"
                "• Give a compliance score (0-100)")
            return

        # Greeting
        if is_greeting(body) and session["state"] == "IDLE":
            send_text(from_number,
                "Welcome to Nyaya-Setu 🏛️\n\n"
                "How can I help you?\n\n"
                "1️⃣ Describe a legal problem — I'll analyse your case under BNS 2023\n\n"
                "2️⃣ Type *check document* — Send an FIR or legal notice for BNS compliance check\n\n"
                "3️⃣ Send a photo — I'll generate a BSA Section 63 evidence certificate\n\n"
                "Type *reset* anytime to start over.")
            return

        # Case conversation
        await handle_conversation(from_number, body, session)

    except Exception:
        print(f"[ERROR] {traceback.format_exc()}")
        send_text(from_number, "Something went wrong. Please try again or type reset.")


# ── Case conversation ──────────────────────────────────────────────────────────
async def handle_conversation(from_number, body, session):
    session["mode"] = "case"
    judge = get_judge(from_number)

    if session["state"] == "IDLE":
        session["state"] = "ACTIVE"
        reply = judge.start(body)
    else:
        reply = judge.reply(body)

    send_text(from_number, reply)

    if judge.has_judgement() and session["state"] == "ACTIVE":
        session["state"] = "AWAITING_EVIDENCE"
        send_text(from_number,
            "📸 Do you have evidence (photo/screenshot)?\n"
            "Send it now and I'll generate a BSA Section 63 certificate.")


# ── PDF compliance check ───────────────────────────────────────────────────────
async def handle_pdf(from_number, media_url, session):
    send_text(from_number, "📋 Reading document...")
    pdf_bytes = download_media(media_url)
    text      = extract_text_from_pdf_bytes(pdf_bytes)

    if text.startswith("ERROR"):
        send_text(from_number, f"Could not read PDF. {text}")
        return

    result  = compute_compliance_score(text)
    message = generate_migration_message(result)
    send_text(from_number, message)
    session["state"] = "IDLE"


# ── Image handler ──────────────────────────────────────────────────────────────
async def handle_image(from_number, media_url, media_type, session):
    img_bytes = download_media(media_url)

    # If in compliance mode or AWAITING_DOCUMENT — try OCR
    if session.get("mode") == "compliance" or session.get("state") == "AWAITING_DOCUMENT":
        send_text(from_number, "📋 Reading document image...")
        text = extract_text_from_image_bytes(img_bytes)
        if text and not text.startswith("ERROR") and len(text) > 50:
            result  = compute_compliance_score(text)
            message = generate_migration_message(result)
            send_text(from_number, message)
        else:
            # Fall through to evidence certificate
            await generate_evidence_cert(from_number, img_bytes, media_type, session)
        session["state"] = "IDLE"
        session["mode"]  = "case"
        return

    # Otherwise — generate evidence certificate
    await generate_evidence_cert(from_number, img_bytes, media_type, session)


async def generate_evidence_cert(from_number, img_bytes, media_type, session):
    send_text(from_number, "🔐 Generating BSA Section 63 evidence certificate...")

    ext      = "jpg" if "jpeg" in media_type else media_type.split("/")[-1]
    filename = f"evidence_{from_number.replace('+','')}_{int(time.time())}.{ext}"

    judge          = get_judge(from_number)
    incident_brief = judge.get_summary()

    cert, pdf_bytes = generate_evidence_certificate(
        file_bytes=img_bytes,
        file_name=filename,
        complainant_name="Unknown",
        incident_brief=incident_brief,
    )

    pdf_name = f"Certificate_NS-{cert.certificate_id}.pdf"
    pdf_url  = save_and_get_url(pdf_bytes, pdf_name)

    msg = (
        f"BSA Section 63 Certificate\n\n"
        f"ID: NS-{cert.certificate_id}\n"
        f"SHA-256: {cert.sha256_hash[:24]}...\n"
        f"Device: {cert.device_make} {cert.device_model}\n"
        f"GPS: {cert.gps_coordinates}\n"
        f"Captured: {cert.capture_timestamp}\n"
        f"Status: {cert.verification_status}\n\n"
        f"Complaint: {incident_brief[:100]}\n\n"
        f"Certificate: {pdf_url}\n\n"
        f"Verify: sha256sum <file> (Linux/Mac)\n"
        f"certutil -hashfile <file> SHA256 (Windows)\n\n"
        f"Legal basis: {cert.bsa_section}\n\n"
        f"Present this certificate with the original photo to the investigating officer."
    )
    send_text(from_number, msg)
    session["state"] = "DONE"


# ── API ────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status":"ok","version":"5.0.0","sessions":len(sessions)}

@app.get("/media/{filename}")
def serve_media(filename: str):
    path = os.path.join("temp_media", filename)
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse({"error":"not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)