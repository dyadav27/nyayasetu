"""
Nyaya-Setu — FastAPI Main Application (v3)
Full conversation state machine with proper evidence certificate linking.

STATES: IDLE → AWAITING_EVIDENCE → DONE
"""

import os, time, traceback
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from m2_rag.rag_engine import get_rag_engine
from m3_evidence.evidence import generate_evidence_certificate

load_dotenv()

# ── Twilio ─────────────────────────────────────────────────────────────────────
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
NGROK_URL    = os.getenv("NGROK_URL", "http://localhost:8000")
twilio       = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

# ── Session store ──────────────────────────────────────────────────────────────
sessions: dict = {}

def new_session(phone: str) -> dict:
    return {
        "phone":          phone,
        "state":          "IDLE",
        "name":           "Unknown",
        "complaint_text": "",          # raw complaint typed by user
        "last_fir":       None,        # FIRComplaint pydantic object from RAG
        "evidence_cert":  None,        # EvidenceCertificate object
        "history":        [],
        "created_at":     time.time(),
    }

def get_session(phone: str) -> dict:
    if phone not in sessions:
        sessions[phone] = new_session(phone)
    return sessions[phone]

def add_history(session: dict, role: str, text: str):
    session["history"].append({"role": role, "text": text})
    if len(session["history"]) > 10:
        session["history"] = session["history"][-10:]

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Nyaya-Setu", version="3.0.0")

_rag = None
def get_rag():
    global _rag
    if _rag is None:
        _rag = get_rag_engine()
    return _rag

# ── Twilio helpers ─────────────────────────────────────────────────────────────
def send_text(to: str, body: str):
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
GREETINGS  = {"hi","hello","namaste","start","help","hey","hii","helo"}
RESET_W    = {"reset","restart","new","clear","start over"}
YES_W      = {"yes","yeah","haan","ha","ok","okay","sure","y","yep","send"}
NO_W       = {"no","nahi","nope","n","skip","later"}
EVIDENCE_W = {"evidence","photo","image","pic","screenshot","proof","picture"}
FOLLOWUP_W = {"what","how","can","will","should","is","are","does","explain",
              "tell","more","about","punishment","penalty","bail","section",
              "fine","jail","arrest","charge","define","meaning","shall"}

def is_greeting(t):    return t.lower().strip() in GREETINGS
def is_reset(t):       return any(w in t.lower() for w in RESET_W)
def is_yes(t):         return t.lower().strip() in YES_W
def is_no(t):          return t.lower().strip() in NO_W
def wants_evidence(t): return any(w in t.lower() for w in EVIDENCE_W)
def is_followup(t):    return any(w in t.lower().split() for w in FOLLOWUP_W)

# ── Webhook ────────────────────────────────────────────────────────────────────
@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form        = await request.form()
    from_number = str(form.get("From", "")).replace("whatsapp:", "")
    body        = str(form.get("Body", "")).strip()
    num_media   = int(form.get("NumMedia", 0))
    media_url   = str(form.get("MediaUrl0", ""))
    media_type  = str(form.get("MediaContentType0", ""))
    session     = get_session(from_number)

    print(f"\n[MSG] {from_number[-4:]} | state={session['state']} | '{body[:60]}'")
    print(f"[MSG] complaint_in_session='{session['complaint_text'][:60]}'")

    background_tasks.add_task(
        handle_message, from_number, body, num_media, media_url, media_type, session
    )
    return PlainTextResponse(str(MessagingResponse()), media_type="application/xml")

# ── Main router ────────────────────────────────────────────────────────────────
async def handle_message(from_number, body, num_media, media_url, media_type, session):
    try:
        add_history(session, "user", body or f"[{media_type}]")

        # Reset — works from any state
        if is_reset(body):
            sessions[from_number] = new_session(from_number)
            send_text(from_number, "🔄 *Conversation reset.*\n\nDescribe your legal problem to begin.")
            return

        # Image — generate evidence certificate linked to current session complaint
        if num_media > 0 and "image" in media_type:
            await handle_image(from_number, media_url, media_type, session)
            return

        # Audio
        if num_media > 0 and "audio" in media_type:
            send_text(from_number,
                "🎙️ Voice processing coming soon.\n"
                "Please *type* your complaint in English for now.")
            return

        # Route by state
        state = session["state"]
        if state == "IDLE":
            await handle_idle(from_number, body, session)
        elif state == "AWAITING_EVIDENCE":
            await handle_awaiting_evidence(from_number, body, session)
        elif state == "DONE":
            await handle_done(from_number, body, session)

    except Exception:
        print(f"[ERROR] {traceback.format_exc()}")
        send_text(from_number, "⚠️ Error. Please try again or type *reset*.")

# ── IDLE ───────────────────────────────────────────────────────────────────────
async def handle_idle(from_number, body, session):
    if is_greeting(body) or not body:
        send_text(from_number,
            "🏛️ *Nyaya-Setu — Bridge to Justice*\n\n"
            "I analyse cases under:\n"
            "• *BNS 2023* — Bharatiya Nyaya Sanhita\n"
            "• *BNSS 2023* — Bharatiya Nagarik Suraksha Sanhita\n"
            "• *BSA 2023* — Bharatiya Sakshya Adhiniyam\n\n"
            "📝 *Describe your problem:*\n"
            "_Example: My employer has not paid salary for 3 months_\n"
            "_Example: Someone snatched my phone near Andheri station_\n"
            "_Example: My landlord locked my flat without notice_\n\n"
            "📸 Send a photo anytime for BSA evidence certification.\n"
            "Type *reset* to start over.")
        return
    await run_legal_analysis(from_number, body, session)

# ── Core legal analysis ────────────────────────────────────────────────────────
async def run_legal_analysis(from_number, complaint, session):
    """
    Runs RAG query and returns full legal judgement:
    - Exact BNS/BNSS/BSA sections that apply
    - What each section means for this specific case
    - Legal assessment and available relief
    Saves complaint_text and last_fir to session for evidence certificate linking.
    """
    # SAVE complaint to session BEFORE querying
    session["complaint_text"] = complaint
    session["state"] = "PROCESSING"

    print(f"[RAG] Saved complaint to session: '{complaint[:80]}'")

    send_text(from_number, "⚖️ Analysing under BNS/BNSS/BSA 2023...")

    rag = get_rag()
    fir = rag.query(complaint, complainant_name=session.get("name", "Unknown"))

    # SAVE fir to session for evidence certificate
    session["last_fir"] = fir
    session["state"]    = "AWAITING_EVIDENCE"

    print(f"[RAG] Saved FIR to session. incident_description: '{fir.incident_description[:80]}'")

    # Build sections block
    sections_text = ""
    for i, (sec, expl) in enumerate(zip(fir.applicable_sections, fir.section_explanations), 1):
        sections_text += f"*{i}. {sec}*\n{expl}\n\n"
    if not sections_text:
        sections_text = "_No specific sections identified. Please provide more details._\n\n"

    # Build steps block
    steps_text = "\n".join(
        f"{i}. {s}" for i, s in enumerate(fir.recommended_next_steps, 1)
    ) if fir.recommended_next_steps else "1. Consult a legal advocate."

    reply = (
        f"⚖️ *Legal Analysis — Nyaya-Setu*\n"
        f"{'─'*30}\n\n"
        f"📋 *Your Complaint:*\n_{complaint[:150]}_\n\n"
        f"{'─'*30}\n\n"
        f"🔖 *Applicable Provisions:*\n\n{sections_text}"
        f"{'─'*30}\n\n"
        f"⚡ *Legal Assessment:*\n_{fir.incident_description}_\n\n"
        f"🎯 *Relief/Remedy Available:*\n_{fir.relief_sought}_\n\n"
        f"{'─'*30}\n\n"
        f"📌 *Recommended Actions:*\n{steps_text}\n\n"
        f"{'─'*30}\n\n"
        f"💬 *Next:*\n"
        f"• Reply *yes* to attach evidence photo\n"
        f"• Reply *no* to finish\n"
        f"• Ask a follow-up question\n"
        f"• Type a new complaint\n"
        f"• Type *reset* to clear\n\n"
        f"⚠️ _{fir.legal_disclaimer}_"
    )

    send_text(from_number, reply)
    add_history(session, "bot", reply)

# ── AWAITING_EVIDENCE ──────────────────────────────────────────────────────────
async def handle_awaiting_evidence(from_number, body, session):
    if is_yes(body) or wants_evidence(body):
        send_text(from_number,
            "📸 *Send your evidence photo now.*\n\n"
            "I will generate a *BSA Section 63 certificate* with:\n"
            "• SHA-256 cryptographic hash\n"
            "• Your complaint details\n"
            "• Device info and GPS location\n"
            "• Timestamp of capture\n\n"
            "_Send the photo directly in this chat._")

    elif is_no(body):
        fir = session.get("last_fir")
        send_text(from_number,
            "✅ *Analysis complete.*\n\n"
            "You can:\n"
            "• Type a *new complaint* anytime\n"
            "• Send a *photo* for evidence certification\n"
            "• Ask follow-up questions\n"
            "• Type *reset* to start fresh\n\n"
            f"⚠️ _{fir.legal_disclaimer if fir else 'Consult a qualified advocate.'}_")
        session["state"] = "DONE"

    elif is_followup(body) or len(body.split()) <= 8:
        # Short message = follow-up question about current case
        prev = session.get("complaint_text", "")
        if prev:
            combined = f"Regarding this case: '{prev[:100]}'. Question: {body}"
            await run_legal_analysis(from_number, combined, session)
        else:
            await run_legal_analysis(from_number, body, session)

    else:
        # Long message = new complaint
        await run_legal_analysis(from_number, body, session)

# ── DONE ───────────────────────────────────────────────────────────────────────
async def handle_done(from_number, body, session):
    if is_greeting(body):
        send_text(from_number,
            "👋 Send your complaint or question.\nType *reset* to clear history.")
        return
    if wants_evidence(body):
        send_text(from_number, "📸 Send your photo directly in this chat.")
        session["state"] = "AWAITING_EVIDENCE"
        return
    await run_legal_analysis(from_number, body, session)

# ── Image / Evidence (M3) ──────────────────────────────────────────────────────
async def handle_image(from_number, media_url, media_type, session):
    """
    Generate BSA Section 63 certificate.
    KEY FIX: Uses session complaint_text and last_fir.incident_description
    so the certificate is always linked to the current complaint.
    """
    send_text(from_number, "🔐 Generating BSA Section 63 Evidence Certificate...")

    # Download image
    img_bytes = download_media(media_url)
    ext       = "jpg" if "jpeg" in media_type else media_type.split("/")[-1]
    filename  = f"evidence_{from_number.replace('+','')}_{int(time.time())}.{ext}"

    # Get complaint context from session
    complaint_text = session.get("complaint_text", "")
    fir            = session.get("last_fir")

    print(f"[M3] complaint_text from session: '{complaint_text[:80]}'")
    print(f"[M3] last_fir exists: {fir is not None}")
    if fir:
        print(f"[M3] fir.incident_description: '{fir.incident_description[:80]}'")

    # Build incident_brief — priority order:
    # 1. FIR incident description (most specific, RAG-generated)
    # 2. Raw complaint text from user
    # 3. Generic fallback
    if fir and fir.incident_description and len(fir.incident_description) > 10 and "See raw" not in fir.incident_description:
        incident_brief = fir.incident_description[:300]
        print(f"[M3] Using FIR incident_description")
    elif complaint_text and len(complaint_text) > 5:
        incident_brief = complaint_text[:300]
        print(f"[M3] Using raw complaint_text")
    else:
        incident_brief = f"Evidence submitted via Nyaya-Setu. User: {from_number[-4:]}"
        print(f"[M3] Using generic fallback — no complaint in session")

    print(f"[M3] Final incident_brief: '{incident_brief[:80]}'")

    # Generate certificate with linked complaint context
    cert, pdf_bytes = generate_evidence_certificate(
        file_bytes=img_bytes,
        file_name=filename,
        complainant_name=session.get("name", "Unknown"),
        incident_brief=incident_brief,
    )
    session["evidence_cert"] = cert

    # Save PDF and get URL
    pdf_name = f"BSA_Certificate_NS-{cert.certificate_id}.pdf"
    pdf_url  = save_and_get_url(pdf_bytes, pdf_name)

    # Show which sections this evidence supports
    linked_sections = ""
    if fir and fir.applicable_sections:
        linked_sections = (
            "\n\n📋 *Evidence supports complaint under:*\n"
            + "\n".join(f"• {s}" for s in fir.applicable_sections[:3])
        )

    msg = (
        f"✅ *BSA Section 63 Evidence Certificate*\n"
        f"{'─'*30}\n\n"
        f"🔐 *SHA-256 Hash:*\n`{cert.sha256_hash}`\n\n"
        f"📄 *Certificate ID:* NS-{cert.certificate_id}\n"
        f"📁 *File:* {cert.file_name}\n"
        f"   Size: {int(cert.file_size_bytes/1024)} KB | "
        f"{cert.image_width}×{cert.image_height} px\n"
        f"📱 *Device:* {cert.device_make} {cert.device_model}\n"
        f"📍 *GPS:* {cert.gps_coordinates}\n"
        f"🕒 *Captured:* {cert.capture_timestamp}\n"
        f"✅ *Integrity:* {cert.verification_status}"
        f"{linked_sections}\n\n"
        f"{'─'*30}\n\n"
        f"📝 *Complaint in Certificate:*\n_{incident_brief[:120]}_\n\n"
        f"📎 *Download Certificate PDF:*\n{pdf_url}\n\n"
        f"🔎 *Verify on your device:*\n"
        f"Windows: `certutil -hashfile <file> SHA256`\n"
        f"Linux/Mac: `sha256sum <file>`\n\n"
        f"⚖️ *Legal basis:* {cert.bsa_section}\n\n"
        f"_Present certificate + original photo to investigating officer._\n\n"
        f"Type a new complaint or *reset* to start fresh."
    )

    send_text(from_number, msg)
    add_history(session, "bot", f"Certificate NS-{cert.certificate_id} generated")
    session["state"] = "DONE"

# ── API endpoints ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status":   "ok",
        "service":  "nyayasetu",
        "version":  "3.0.0",
        "sessions": len(sessions),
        "rag_loaded": _rag is not None,
    }

@app.get("/stats")
def stats():
    return {
        "active_sessions": len(sessions),
        "sessions": [
            {
                "phone_last4":    s["phone"][-4:],
                "state":          s["state"],
                "complaint":      s["complaint_text"][:60] if s["complaint_text"] else "",
                "has_fir":        s["last_fir"] is not None,
                "has_certificate": s["evidence_cert"] is not None,
            }
            for s in sessions.values()
        ]
    }

@app.get("/media/{filename}")
def serve_media(filename: str):
    path = os.path.join("temp_media", filename)
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse({"error": "file not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)