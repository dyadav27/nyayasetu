"""
api.py — FastAPI Backend for Nyaya-Setu Website
Nyaya-Setu | Team IKS | SPIT CSE 2025-26
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, time, uuid, random, string
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

from document_analyzer import analyze_document, DocumentRAG, fetch_case_laws, fetch_acts
from lex_validator import (
    compute_compliance_score,
    generate_migration_message,
    extract_text_from_pdf_bytes,
)
from modules.m3_evidence.evidence import generate_evidence_certificate
from legal_translator import translate_legal_text, translate_fir, get_supported_languages

from sqlalchemy.orm import Session
from fastapi import Depends
import models
from models import StatutoryAct
from database import engine, get_db
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from datetime import timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

# Create database tables
models.Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str = None

class UserLogin(BaseModel):
    email: str
    password: str

class CaseCreate(BaseModel):
    title: str
    cnr_number: str = None
    court_name: str = None
    client_name: str = None
    status: str = "Active"

class CaseResponse(BaseModel):
    id: int
    title: str
    cnr_number: str = None
    court_name: str = None
    client_name: str = None
    status: str
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    description: str = None
    due_date: str
    case_id: int = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str = None
    due_date: str
    is_completed: bool
    case_id: int = None
    
    class Config:
        from_attributes = True

class HearingCreate(BaseModel):
    case_id: int
    hearing_date: str
    purpose: str
    notes: str = None

class HearingResponse(BaseModel):
    id: int
    case_id: int
    hearing_date: str
    purpose: str
    notes: str = None
    
    class Config:
        from_attributes = True

class InvoiceCreate(BaseModel):
    client_name: str
    amount: float
    due_date: str

class InvoiceResponse(BaseModel):
    id: int
    client_name: str
    amount: float
    status: str
    due_date: str
    created_at: str

    class Config:
        from_attributes = True

class DocumentGenerateRequest(BaseModel):
    doc_type: str # Rent Agreement, Legal Notice
    party_a: str
    party_b: str
    details: str

class ResearchAskRequest(BaseModel):
    query: str

class ResearchCaseRequest(BaseModel):
    query: str
    court: str = "All Courts"
    year_from: str = ""
    year_to: str = ""
    page: int = 0

class ResearchSectionRequest(BaseModel):
    sections: str
    act: str
    page: int = 0

class ResearchActRequest(BaseModel):
    act_name: str
    jurisdiction: str = "Union of India"

class ResearchActsListRequest(BaseModel):
    jurisdiction: Optional[str] = None
    category: Optional[str] = None
    page: int = 0

class CopilotRequest(BaseModel):
    prompt: str
    document_context: str = ""

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

# ── Authentication & Users ────────────────────────────────────────────────────
@app.post("/api/auth/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully", "user_id": db_user.id}

@app.post("/api/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email, "role": db_user.role, "id": db_user.id}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": db_user.id, "email": db_user.email, "full_name": db_user.full_name, "role": db_user.role}}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/api/auth/me")
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "phone": current_user.phone
    }

# ── Case Management ───────────────────────────────────────────────────────────
@app.post("/api/cases", response_model=CaseResponse)
def create_case(case: CaseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_case = models.Case(
        title=case.title,
        cnr_number=case.cnr_number,
        court_name=case.court_name,
        client_name=case.client_name,
        status=case.status,
        lawyer_id=current_user.id
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@app.get("/api/cases")
def get_cases(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "admin":
        cases = db.query(models.Case).all()
    else:
        cases = db.query(models.Case).filter(models.Case.lawyer_id == current_user.id).all()
    return cases

@app.get("/api/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.lawyer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
    return case

@app.get("/api/cnr/{cnr_number}")
def fetch_mock_cnr(cnr_number: str):
    """Mock endpoint to simulate E-Courts API data fetch based on CNR number."""
    if len(cnr_number) < 16:
        raise HTTPException(status_code=400, detail="Invalid CNR number format. Must be 16 characters.")
    
    # Mock data generation based on string to make it deterministic but varied
    import random
    random.seed(cnr_number)
    
    courts = ["Supreme Court of India", "Delhi High Court", "Bombay High Court", "District Court Saket"]
    statuses = ["Active", "Pending Hearing", "Disposed", "Reserved for Orders"]
    
    return {
        "cnr_number": cnr_number,
        "title": f"State vs. Mock Person {random.randint(1, 100)}",
        "court_name": random.choice(courts),
        "status": random.choice(statuses),
        "filing_date": f"2023-0{random.randint(1,9)}-{random.randint(10,28)}",
        "next_hearing": f"2026-0{random.randint(6,9)}-{random.randint(10,28)}"
    }

# ── Tasks & Hearings ──────────────────────────────────────────────────────────
@app.post("/api/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    db_task = models.Task(
        title=task.title,
        description=task.description,
        due_date=datetime.fromisoformat(task.due_date.replace("Z", "+00:00")),
        case_id=task.case_id,
        assignee_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    # Ensure datetime is formatted as string in response to match Pydantic schema easily
    task_dict = db_task.__dict__.copy()
    task_dict['due_date'] = str(db_task.due_date)
    return task_dict

@app.get("/api/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tasks = db.query(models.Task).filter(models.Task.assignee_id == current_user.id).all()
    res = []
    for t in tasks:
        td = t.__dict__.copy()
        td['due_date'] = str(t.due_date)
        res.append(td)
    return res

@app.post("/api/hearings", response_model=HearingResponse)
def create_hearing(hearing: HearingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    # Ensure user has access to case
    case = db.query(models.Case).filter(models.Case.id == hearing.case_id).first()
    if not case or (case.lawyer_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to add hearing to this case")
        
    db_hearing = models.Hearing(
        case_id=hearing.case_id,
        hearing_date=datetime.fromisoformat(hearing.hearing_date.replace("Z", "+00:00")),
        purpose=hearing.purpose,
        notes=hearing.notes
    )
    db.add(db_hearing)
    db.commit()
    db.refresh(db_hearing)
    hd = db_hearing.__dict__.copy()
    hd['hearing_date'] = str(db_hearing.hearing_date)
    return hd

@app.get("/api/hearings", response_model=list[HearingResponse])
def get_hearings(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Get all cases for user
    cases = db.query(models.Case).filter(models.Case.lawyer_id == current_user.id).all()
    case_ids = [c.id for c in cases]
    hearings = db.query(models.Hearing).filter(models.Hearing.case_id.in_(case_ids)).all()
    res = []
    for h in hearings:
        hd = h.__dict__.copy()
        hd['hearing_date'] = str(h.hearing_date)
        res.append(hd)
    return res

# ── Firm Billing ──────────────────────────────────────────────────────────────
@app.post("/api/invoices", response_model=InvoiceResponse)
def create_invoice(inv: InvoiceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from datetime import datetime
    db_inv = models.Invoice(
        lawyer_id=current_user.id,
        client_name=inv.client_name,
        amount=inv.amount,
        due_date=datetime.fromisoformat(inv.due_date.replace("Z", "+00:00"))
    )
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    inv_dict = db_inv.__dict__.copy()
    inv_dict['due_date'] = str(db_inv.due_date)
    inv_dict['created_at'] = str(db_inv.created_at)
    return inv_dict

@app.get("/api/invoices", response_model=list[InvoiceResponse])
def get_invoices(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "admin":
        invoices = db.query(models.Invoice).all()
    else:
        invoices = db.query(models.Invoice).filter(models.Invoice.lawyer_id == current_user.id).all()
        
    res = []
    for inv in invoices:
        inv_dict = inv.__dict__.copy()
        inv_dict['due_date'] = str(inv.due_date)
        inv_dict['created_at'] = str(inv.created_at)
        res.append(inv_dict)
    return res

# ── Document Generator ────────────────────────────────────────────────────────
@app.post("/api/generate_doc")
def generate_document(req: DocumentGenerateRequest, current_user: models.User = Depends(get_current_user)):
    """Generate legal documents via templates."""
    if req.doc_type == "Rent Agreement":
        content = f"""
RENT AGREEMENT

This Rent Agreement is made on this day between {req.party_a} (hereinafter referred to as the 'Landlord') 
and {req.party_b} (hereinafter referred to as the 'Tenant').

WHEREAS the Landlord is the absolute owner of the property and the Tenant has agreed to take the same on rent.

DETAILS OF AGREEMENT:
{req.details}

1. The Tenant shall pay the agreed monthly rent in advance.
2. The Tenant shall not sublet the property.
3. The Agreement is subject to the jurisdiction of local courts.

Signatures:
_______________________ (Landlord: {req.party_a})
_______________________ (Tenant: {req.party_b})
"""
    elif req.doc_type == "Legal Notice":
        content = f"""
LEGAL NOTICE

To: {req.party_b}
From: {req.party_a}

Under instruction from my client {req.party_a}, I hereby issue this legal notice to you.

SUBJECT: {req.details}

You are hereby called upon to comply with the demands mentioned above within 15 days of receiving this notice, failing which my client shall be constrained to initiate legal proceedings against you entirely at your risk and cost.

Signed,
{current_user.full_name}, Advocate
"""
    else:
        content = "Document type not supported."
        
    return {"doc_type": req.doc_type, "content": content}

# ── Research Section (Real Endpoints) ─────────────────────────────────────────

from document_analyzer import call_llm, fetch_case_laws, parse_json_response

@app.post("/api/research/ask")
def research_ask(req: ResearchAskRequest):
    # Fetch real case precedents from Indian Kanoon first
    cases = fetch_case_laws(req.query, "Legal Question")
    
    # Build a context string from the retrieved Kanoon judgments
    context_str = ""
    for idx, c in enumerate(cases):
        context_str += f"[{idx+1}] Case: {c.get('title', 'Unknown')}\nSummary: {c.get('summary', '')}\n\n"

    # Use Groq to synthesize an answer backed by these real Kanoon cases
    prompt = f"""You are an expert Indian Legal Researcher. Provide a comprehensive, accurate, and easy-to-understand answer to the following legal question based on Indian law and the provided Supreme Court / High Court judgments.

Structure your answer with these exact three headings:
Applicable Law
Application
Conclusion

QUESTION: {req.query}

RELEVANT JUDGMENTS (Fetched from Indian Kanoon):
{context_str if context_str.strip() else "No specific case laws found, answer based on general Indian legal principles."}

Base your answer heavily on these specific judgments if provided. You MUST explicitly cite them in your text using their index number in brackets (e.g., [1], [2])."""
    
    response = call_llm(prompt, temperature=0.2)
    return {"response": response, "citations": cases}

@app.post("/api/research/cases")
def research_cases(req: ResearchCaseRequest):
    # If court or year filters are provided, we can append them to the query
    search_query = req.query
    if req.court and req.court != "All Courts":
        search_query += f" {req.court}"
    if req.year_from:
        search_query += f" {req.year_from}"
    
    cases = fetch_case_laws(search_query, "Case Search", pagenum=req.page)
    # fetch_case_laws returns a list of dicts: title, summary, url, court, year, related_section
    # We map this to the format expected by the frontend
    results = [
        {
            "title": c.get("title", "Untitled"),
            "court": c.get("court", "Indian Court"),
            "year": c.get("year", ""),
            "snippet": c.get("summary", ""),
            "url": c.get("url", "")
        }
        for c in cases
    ]
    return {"results": results}

@app.post("/api/research/sections")
def research_sections(req: ResearchSectionRequest):
    search_query = f"Section {req.sections} of {req.act}"
    cases = fetch_case_laws(search_query, "Section Search", pagenum=req.page)
    results = [
        {
            "title": c.get("title", "Untitled"),
            "court": c.get("court", "Indian Court"),
            "year": c.get("year", ""),
            "snippet": c.get("summary", ""),
            "url": c.get("url", "")
        }
        for c in cases
    ]
    return {"results": results}

@app.post("/api/research/acts")
def research_acts(req: ResearchActsListRequest, db: Session = Depends(get_db)):
    query = db.query(StatutoryAct)
    
    if req.jurisdiction:
        query = query.filter(StatutoryAct.jurisdiction == req.jurisdiction)
        
    if req.category and req.category != "All":
        query = query.filter(StatutoryAct.category.like(f"%{req.category}%"))
        
    acts = query.limit(50).all() # Return up to 50 acts at once from our database
    
    results = [
        {
            "name": a.title,
            "year": a.year,
            "snippet": a.summary,
            "url": a.url
        }
        for a in acts
    ]
    return {"acts": results}

@app.post("/api/research/act_summary")
def research_act_summary(req: ResearchActRequest):
    prompt = f"""You are an expert Indian Legal Assistant. Summarize the following statutory act.
Act Name: {req.act_name}
Jurisdiction: {req.jurisdiction}

Return a JSON object strictly following this structure:
{{
  "purpose": "A paragraph explaining the objective, factual background, and purpose of the act.",
  "key_provisions": "A paragraph detailing the most important sections and operational mechanisms of the act.",
  "implications": "A paragraph explaining the legal implications, penalties, or overall impact of the act."
}}
Return ONLY valid JSON, without any markdown formatting like ```json or ```."""
    
    raw_response = call_llm(prompt, temperature=0.1)
    data = parse_json_response(raw_response, fallback={
        "purpose": "Failed to generate purpose.",
        "key_provisions": "Could not parse key provisions.",
        "implications": "Could not parse implications."
    })
    return data

@app.post("/api/editor/copilot")
def editor_copilot(req: CopilotRequest):
    if not os.getenv("GEMINI_API_KEY"):
        return {"reply": "API Key missing. Cannot connect to copilot."}
        
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        system_prompt = """You are an elite legal drafting AI Copilot, acting as a Senior Partner at a top-tier Indian law firm. 
Your primary job is to generate top-notch, watertight, and highly professional legal clauses, pleadings, and correspondence.
Follow these strict rules:
1. ALWAYS default to Indian Law (e.g., BNSS, BNS, BSA, CPC, Indian Contract Act) and Indian jurisdictions (e.g., Mumbai, Delhi) unless specified otherwise.
2. Use precise, formal, and authoritative legal terminology standard in Indian High Courts and the Supreme Court.
3. If asked to draft a clause, provide ONLY the drafted clause itself, ready to be inserted directly into the document. DO NOT include conversational filler like 'Here is a draft...' or 'Would you like to customize this...'.
4. Ensure all drafting is unambiguous, comprehensive, and protects the client's interests.
5. Provide plain text output without markdown formatting (no **, ##, etc.) to ensure seamless pasting into a rich text editor."""
        
        full_prompt = f"User Request: {req.prompt}\n\nCurrent Document Context (use this to match party names, tone, and subject matter if applicable):\n{req.document_context[:2000]}\n\nDraft exactly what is requested based on the rules above."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )
        return {"reply": response.text}
    except Exception as e:
        print(f"Copilot Error: {e}")
        return {"reply": "Sorry, I encountered an error while generating the text."}

@app.get("/api/research/topics")
def research_topics():
    return {
        "topics": [
            {"name": "Constitutional & Administrative", "count": 6},
            {"name": "Criminal Law", "count": 6},
            {"name": "Civil & Property", "count": 8},
            {"name": "Corporate & Commercial", "count": 6},
            {"name": "Tax Laws", "count": 8},
            {"name": "Labour & Service", "count": 2}
        ]
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