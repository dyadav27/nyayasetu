"""
document_analyzer.py — Core Document Analysis Engine
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Handles:
  1.  PDF/image text extraction
  2.  Clause segmentation
  3.  Clause risk scoring (Safe/Caution/High Risk/Illegal)
  4.  Plain-language document summary
  5.  Confidence scoring on every output
  6.  IndianKanoon case law retrieval
  7.  RAG Q&A over uploaded document (multi-turn)
  NEW:
  8.  Document type detection with confidence %
  9.  Party obligation map
  10. Missing clauses detector
  11. Plain-English rewrite for High Risk / Illegal clauses (safer_version)
  12. Key numbers extractor (rupees, dates, %, durations)
  13. Limitation period / deadline alerts
  14. Suggested questions (6 per document)
  15. Signature verdict (Sign / Negotiate / Do Not Sign)
"""

import os, sys, re, json
import requests as req
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz          # PyMuPDF
from groq import Groq
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from dotenv import load_dotenv
from gpu_utils import DEVICE
from legal_translator import detect_language_with_llm, translate_legal_text
import base64

load_dotenv()

GROQ_MODEL           = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
INDIANKANOON_API_KEY = os.getenv("INDIANKANOON_API_KEY", "")
EMBED_MODEL = "all-MiniLM-L6-v2"   # resolved from HuggingFace cache automatically

# ── Groq client ────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────────────────────
# Document type definitions — required clauses per type
# ─────────────────────────────────────────────────────────────
DOCUMENT_TYPES = {
    "rental_agreement": {
        "label":    "Rental Agreement",
        "keywords": ["tenancy", "rent", "landlord", "tenant", "premises", "lease", "monthly rent"],
        "required_clauses": [
            "Termination clause",
            "Maintenance clause",
            "Security deposit clause",
            "Notice period clause",
            "Rent escalation clause",
            "Subletting / lock-in clause",
        ],
    },
    "employment_contract": {
        "label":    "Employment Contract",
        "keywords": ["employment", "salary", "employer", "employee", "designation", "joining", "probation"],
        "required_clauses": [
            "Probation period clause",
            "Notice period clause",
            "Non-disclosure / confidentiality clause",
            "Termination clause",
            "Salary revision clause",
            "Intellectual property clause",
        ],
    },
    "loan_agreement": {
        "label":    "Loan Agreement",
        "keywords": ["loan", "borrower", "lender", "emi", "repayment", "collateral", "interest rate"],
        "required_clauses": [
            "Repayment schedule clause",
            "Interest rate clause",
            "Default clause",
            "Prepayment clause",
            "Security / collateral clause",
        ],
    },
    "sale_agreement": {
        "label":    "Sale Agreement",
        "keywords": ["sale", "purchase", "buyer", "seller", "payment", "delivery", "goods"],
        "required_clauses": [
            "Payment terms clause",
            "Delivery clause",
            "Warranty clause",
            "Dispute resolution clause",
            "Force majeure clause",
        ],
    },
    "service_agreement": {
        "label":    "Service Agreement",
        "keywords": ["service", "client", "vendor", "deliverable", "milestone", "fee", "scope of work"],
        "required_clauses": [
            "Scope of work clause",
            "Payment terms clause",
            "Confidentiality clause",
            "Termination clause",
            "Liability / indemnity clause",
            "Intellectual property clause",
        ],
    },
    "nda": {
        "label":    "Non-Disclosure Agreement",
        "keywords": ["confidential", "non-disclosure", "proprietary", "disclose", "recipient", "disclosing party"],
        "required_clauses": [
            "Definition of confidential information",
            "Obligations of receiving party",
            "Exclusions clause",
            "Term / duration clause",
            "Return of information clause",
        ],
    },
    "fir": {
        "label":    "FIR / Police Complaint",
        "keywords": ["fir", "first information report", "complainant", "accused", "police station", "offence"],
        "required_clauses": [],
    },
    "legal_notice": {
        "label":    "Legal Notice / Court Document",
        "keywords": ["summon", "notice", "court", "plaintiff", "defendant", "petition", "jurisdiction"],
        "required_clauses": [],
    },
    "unknown": {
        "label":    "General Legal Document",
        "keywords": [],
        "required_clauses": [
            "Termination clause",
            "Dispute resolution clause",
            "Governing law clause",
        ],
    },
}


# ─────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────
class ClauseAnalysis(BaseModel):
    clause_text:   str
    risk_level:    str           # Safe / Caution / High Risk / Illegal
    risk_score:    float         # 0.0–1.0
    explanation:   str
    confidence:    float
    suggestion:    str
    safer_version: Optional[str] = None   # NEW: rewrite for High Risk / Illegal

class PartyObligation(BaseModel):
    party_name:  str
    obligations: list[str]

class MissingClause(BaseModel):
    clause:        str
    present:       bool
    why_important: str

class KeyNumber(BaseModel):
    label: str
    value: str
    type:  str    # monetary / date / percentage / duration / other

class Deadline(BaseModel):
    description: str
    deadline:    str
    consequence: Optional[str] = None

class SignatureVerdict(BaseModel):
    verdict: str   # "Safe to Sign" / "Negotiate First" / "Do Not Sign"
    color:   str   # green / orange / red
    reason:  str

class SectionExplanation(BaseModel):
    section:      str
    title:        str
    explanation:  str
    punishment:   str = ""
    key_elements: list[str] = []

class DocumentAnalysis(BaseModel):
    document_name:       str
    document_type:       str
    document_type_key:   str    # NEW: e.g. "rental_agreement"
    type_confidence:     int    # NEW: 0–100
    total_clauses:       int
    summary:             str
    risk_distribution:   dict
    clauses:             list[ClauseAnalysis]
    overall_risk:        str
    compliance_score:    int
    case_laws:           list[dict]
    recommendations:     list[str]
    # NEW fields
    party_obligations:   list[PartyObligation]
    missing_clauses:     list[MissingClause]
    key_numbers:         list[KeyNumber]
    deadlines:           list[Deadline]
    suggested_questions: list[str]
    signature_verdict:   SignatureVerdict
    original_text:          Optional[str]   = None
    source_language:        Optional[str]   = None
    full_translation:       Optional[str]   = None   # complete English text (shown in Translation tab)
    translation_engine:     Optional[str]   = None   # e.g. "sarvam-indictrans2"
    translation_confidence: Optional[float] = None
    mentioned_sections:     list[str]       = []     # BNS/IPC/CrPC refs found in document
    section_explanations:   list[dict]      = []     # plain-English explanation of each section

class QAResponse(BaseModel):
    question:   str
    answer:     str
    confidence: float
    sources:    list[str]
    disclaimer: str


# ─────────────────────────────────────────────────────────────
# Text extraction & Vision OCR
# ─────────────────────────────────────────────────────────────
def extract_text_with_vision(image_bytes: bytes) -> str:
    """Use Groq Llama 3.2 Vision to extract text from an image."""
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        completion = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text from this image exactly as it appears. Do not add any commentary. If the text is in an Indian language (like Marathi or Hindi), transcribe it perfectly in its native script."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=2048
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[VISION] Failed to extract text: {e}")
        return ""

def extract_text(file_bytes: bytes, filename: str) -> str:
    fname = filename.lower()
    
    # 1. Handle PDFs
    if fname.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc).strip()
        
        # SMART FALLBACK: If it's a scanned PDF, get_text() will return < 50 chars
        if len(text) < 50:
            print("[ANALYZER] PDF seems to be a scanned image. Falling back to Vision OCR...")
            vision_text = []
            # Extract first 3 pages max to prevent API overload
            for page_num in range(min(3, len(doc))):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                extracted = extract_text_with_vision(img_bytes)
                if extracted:
                    vision_text.append(extracted)
            doc.close()
            return "\n\n".join(vision_text).strip()
            
        doc.close()
        return text

    # 2. Handle raw Images
    elif any(fname.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        print("[ANALYZER] Image detected. Using Vision OCR...")
        return extract_text_with_vision(file_bytes)
        
    return ""


# ─────────────────────────────────────────────────────────────
# Clause segmentation
# ─────────────────────────────────────────────────────────────
def segment_clauses(text: str) -> list[str]:
    numbered = re.split(
        r'\n(?=(?:\d+[\.\)]\s)|(?:Clause\s+\d+)|(?:Section\s+\d+)|(?:[A-Z]\.\s))',
        text,
    )
    if len(numbered) > 3:
        return [c.strip() for c in numbered if len(c.strip()) > 30]
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if len(paragraphs) > 2:
        return paragraphs
    words, chunks, chunk = text.split(), [], []
    for word in words:
        chunk.append(word)
        if len(" ".join(chunk)) > 300:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks


# ─────────────────────────────────────────────────────────────
# Document type detection with confidence  (ENHANCED)
# ─────────────────────────────────────────────────────────────
def detect_document_type(text: str) -> tuple[str, str, int]:
    """Returns (type_key, label, confidence_pct)"""
    lower  = text.lower()
    scores = {}
    for key, cfg in DOCUMENT_TYPES.items():
        if key == "unknown" or not cfg["keywords"]:
            continue
        hits = sum(1 for kw in cfg["keywords"] if kw in lower)
        if hits:
            scores[key] = hits / len(cfg["keywords"])

    if not scores:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40

    best_key   = max(scores, key=scores.get)
    confidence = min(int(scores[best_key] * 100), 97)
    if confidence < 20:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40

    return best_key, DOCUMENT_TYPES[best_key]["label"], confidence


# Two-tier model strategy:
#   GROQ_MODEL (70b)        — complex reasoning: summary, section explanations, party obligations
#   GROQ_FAST_MODEL (8b)    — high-volume repetitive: clause analysis, key numbers, deadlines, etc.
# Free-tier TPM limits: 70b = 12,000 | 8b = 30,000
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

import time as _time

def _groq_call(model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    """Raw Groq call with automatic retry on 429 rate-limit errors."""
    for attempt in range(4):
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate_limit" in msg.lower():
                wait = 3 * (attempt + 1)   # 3s, 6s, 9s, 12s
                print(f"[LLM] Rate limit hit. Waiting {wait}s (attempt {attempt+1}/4)...")
                _time.sleep(wait)
            else:
                raise
    raise RuntimeError("Groq rate limit: exceeded max retries")


def call_llm(prompt: str, temperature: float = 0.1) -> str:
    """Use the heavy 70b model — for complex, one-off reasoning tasks."""
    return _groq_call(GROQ_MODEL, prompt, temperature, max_tokens=3000)


def call_llm_fast(prompt: str, temperature: float = 0.1) -> str:
    """Use the fast 8b model — for repetitive clause-level tasks (30k TPM)."""
    return _groq_call(GROQ_FAST_MODEL, prompt, temperature, max_tokens=1500)




def parse_json_response(raw: str, fallback):
    """Strip markdown fences and extract the first JSON array or object."""
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*",     "", raw).strip()
    for pattern in (r'\[.*\]', r'\{.*\}'):
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return fallback


def compute_confidence(context: str, answer: str) -> float:
    uncertainty = ["i'm not sure", "unclear", "cannot determine", "not specified", "ambiguous"]
    certainty   = ["section", "clause", "shall", "must", "rs.", "₹", "days", "months", "%"]
    al    = answer.lower()
    score = 0.6 + sum(0.05 for m in certainty if m in al) - sum(0.15 for m in uncertainty if m in al)
    return round(max(0.1, min(0.95, score)), 2)


# ─────────────────────────────────────────────────────────────
# Clause risk scoring  (ENHANCED — adds safer_version)
# ─────────────────────────────────────────────────────────────
def analyze_clause(clause: str, doc_type: str) -> ClauseAnalysis:
    prompt = f"""You are an Indian legal expert reviewing a {doc_type}.
Analyze this clause and respond ONLY with a valid JSON object — no other text.

CLAUSE:
{clause[:500]}

JSON format:
{{
  "risk_level": "Safe" or "Caution" or "High Risk" or "Illegal",
  "risk_score": 0.0 to 1.0,
  "explanation": "one plain-English sentence explaining why",
  "confidence": 0.0 to 1.0,
  "suggestion": "one sentence on what the user should do",
  "safer_version": "if risk_level is High Risk or Illegal, write a fairer rewrite the user can propose to the other party. Otherwise null."
}}

Risk guide:
- Safe: standard, fair language
- Caution: unusual or one-sided but not illegal
- High Risk: significantly unfair, likely challengeable in court
- Illegal: violates Indian law (Consumer Protection Act, Contract Act, BNS 2023, labour laws)"""

    raw  = call_llm_fast(prompt)
    data = parse_json_response(raw, {})

    return ClauseAnalysis(
        clause_text=clause[:300],
        risk_level=data.get("risk_level", "Caution"),
        risk_score=float(data.get("risk_score", 0.5)),
        explanation=data.get("explanation", "Could not parse this clause automatically."),
        confidence=float(data.get("confidence", 0.5)),
        suggestion=data.get("suggestion", "Review with a lawyer."),
        safer_version=data.get("safer_version") or None,
    )


# ─────────────────────────────────────────────────────────────
# Document summary
# ─────────────────────────────────────────────────────────────
def summarize_document(text: str, doc_type: str) -> str:
    prompt = f"""You are an Indian legal assistant. Summarize this {doc_type} in plain English for a common person.
Under 120 words. Cover: what it is, who the parties are, key obligations, and any major risks.
No headings or bullet points.

DOCUMENT (first 2000 chars):
{text[:2000]}"""
    return call_llm(prompt, temperature=0.2)


# ─────────────────────────────────────────────────────────────
# Party obligation map  (NEW)
# ─────────────────────────────────────────────────────────────
def extract_party_obligations(text: str, doc_type: str) -> list[PartyObligation]:
    prompt = f"""You are an Indian legal expert. From this {doc_type}, extract the obligations of each party.

Return a JSON array:
[
  {{"party_name": "Landlord", "obligations": ["Must maintain the property", "Cannot enter without 24h notice"]}},
  {{"party_name": "Tenant",   "obligations": ["Must pay rent by 5th of each month", "Cannot sublet without permission"]}}
]

Only include obligations clearly stated in the document. Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm(prompt, temperature=0.1)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(PartyObligation(
                party_name=str(item.get("party_name", "Party")),
                obligations=[str(o) for o in item.get("obligations", [])],
            ))
        except Exception:
            pass
    return results


# ─────────────────────────────────────────────────────────────
# Missing clauses detector  (NEW)
# ─────────────────────────────────────────────────────────────
def detect_missing_clauses(text: str, type_key: str) -> list[MissingClause]:
    required = DOCUMENT_TYPES.get(type_key, DOCUMENT_TYPES["unknown"])["required_clauses"]
    if not required:
        return []

    label  = DOCUMENT_TYPES.get(type_key, DOCUMENT_TYPES["unknown"])["label"]
    prompt = f"""You are an Indian legal expert reviewing a {label}.
Check if each of these standard clauses is present in the document.

Clauses to check:
{json.dumps(required)}

Return a JSON array, one item per clause:
[
  {{"clause": "Termination clause",   "present": true,  "why_important": "Defines how either party can exit the agreement."}},
  {{"clause": "Notice period clause", "present": false, "why_important": "Protects you from sudden eviction without warning."}}
]

Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm_fast(prompt, temperature=0.1)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(MissingClause(
                clause=str(item.get("clause", "")),
                present=bool(item.get("present", False)),
                why_important=str(item.get("why_important", "")),
            ))
        except Exception:
            pass

    # Fallback: keyword-based detection if LLM returned nothing
    if not results:
        lower = text.lower()
        for clause in required:
            kws     = [w for w in clause.lower().replace(" clause", "").split() if len(w) > 3]
            present = any(kw in lower for kw in kws)
            results.append(MissingClause(
                clause=clause,
                present=present,
                why_important=f"Standard protection in a {label}.",
            ))
    return results


# ─────────────────────────────────────────────────────────────
# Key numbers extractor  (NEW)
# ─────────────────────────────────────────────────────────────
def extract_key_numbers(text: str) -> list[KeyNumber]:
    prompt = f"""Extract every monetary amount, date, percentage, and duration from this legal document.

Return a JSON array:
[
  {{"label": "Security Deposit", "value": "₹50,000",     "type": "monetary"}},
  {{"label": "Monthly Rent",     "value": "₹15,000",     "type": "monetary"}},
  {{"label": "Notice Period",    "value": "30 days",      "type": "duration"}},
  {{"label": "Start Date",       "value": "1 Jan 2025",   "type": "date"}},
  {{"label": "Late Fee",         "value": "2% per month", "type": "percentage"}}
]

Types: monetary / date / percentage / duration / other
Extract EVERY number — miss nothing.
Return ONLY valid JSON array.

DOCUMENT:
{text[:4000]}"""

    raw  = call_llm_fast(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(KeyNumber(
                label=str(item.get("label", "")),
                value=str(item.get("value", "")),
                type=str(item.get("type",  "other")),
            ))
        except Exception:
            pass
    # Deduplicate by (normalised value, type)
    seen, unique = set(), []
    for n in results:
        key = (re.sub(r'\s+', '', n.value.strip().lower()), n.type)
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique


# ─────────────────────────────────────────────────────────────
# Deadline / limitation period alerts  (NEW)
# ─────────────────────────────────────────────────────────────
def extract_deadlines(text: str) -> list[Deadline]:
    prompt = f"""Extract all deadlines, time limits, and limitation periods from this legal document.

Return a JSON array:
[
  {{"description": "Rent payment",   "deadline": "5th of every month",  "consequence": "2% late fee"}},
  {{"description": "Notice to quit", "deadline": "30 days in advance",  "consequence": "Security deposit forfeited"}}
]

Use null for consequence if not stated.
Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm_fast(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(Deadline(
                description=str(item.get("description", "")),
                deadline=str(item.get("deadline", "")),
                consequence=item.get("consequence") or None,
            ))
        except Exception:
            pass
    return results


# ─────────────────────────────────────────────────────────────
# Suggested questions  (NEW)
# ─────────────────────────────────────────────────────────────
def generate_suggested_questions(text: str, doc_type: str) -> list[str]:
    prompt = f"""You are an Indian legal expert. A user just had their {doc_type} analyzed.
Generate exactly 6 questions they are most likely to ask about this specific document.
Make them concrete and based on the document content — not generic.

Return a JSON array of 6 question strings only.
Example: ["Can the landlord enter without notice?", "What happens if I miss a payment?"]

Return ONLY valid JSON array.

DOCUMENT (first 1500 chars):
{text[:1500]}"""

    raw  = call_llm(prompt, temperature=0.3)
    data = parse_json_response(raw, [])
    if isinstance(data, list) and len(data) >= 3:
        return [str(q) for q in data[:6]]

    return [
        "What are my main obligations under this agreement?",
        "Can the other party terminate without prior notice?",
        "What happens if I miss a payment?",
        "Is there a penalty clause I should know about?",
        "Can I negotiate the high-risk clauses?",
        "Which clauses protect me the most?",
    ]


# ─────────────────────────────────────────────────────────────
# Signature verdict  (NEW)
# ─────────────────────────────────────────────────────────────
def get_signature_verdict(
    clauses: list[ClauseAnalysis],
    missing: list[MissingClause],
) -> SignatureVerdict:
    illegal_count   = sum(1 for c in clauses if c.risk_level == "Illegal")
    high_risk_count = sum(1 for c in clauses if c.risk_level == "High Risk")
    missing_count   = sum(1 for m in missing if not m.present)

    if illegal_count > 0:
        return SignatureVerdict(
            verdict="Do Not Sign",
            color="red",
            reason=f"Contains {illegal_count} illegal clause(s) that violate Indian law. Seek legal counsel before proceeding.",
        )
    if high_risk_count >= 3 or (high_risk_count >= 1 and missing_count >= 2):
        return SignatureVerdict(
            verdict="Negotiate First",
            color="orange",
            reason=f"{high_risk_count} high-risk clause(s) and {missing_count} missing standard protection(s) need to be resolved first.",
        )
    if high_risk_count >= 1 or missing_count >= 2:
        return SignatureVerdict(
            verdict="Negotiate First",
            color="orange",
            reason=f"Review {high_risk_count} risky clause(s) and consider adding {missing_count} missing standard clause(s).",
        )
    return SignatureVerdict(
        verdict="Safe to Sign",
        color="green",
        reason="No illegal or high-risk clauses detected and standard protections appear to be present.",
    )


# ─────────────────────────────────────────────────────────────
# Overall risk
# ─────────────────────────────────────────────────────────────
def compute_overall_risk(clauses: list[ClauseAnalysis]) -> str:
    if not clauses:
        return "Unknown"
    illegal = sum(1 for c in clauses if c.risk_level == "Illegal")
    high    = sum(1 for c in clauses if c.risk_level == "High Risk")
    caution = sum(1 for c in clauses if c.risk_level == "Caution")
    if illegal > 0:              return "Critical"
    if high >= 2:                return "High"
    if high == 1 or caution >= 3: return "Moderate"
    return "Safe"


# ─────────────────────────────────────────────────────────────
# Legal section extraction + explanation
# ─────────────────────────────────────────────────────────────
def extract_legal_sections(text: str) -> list[str]:
    """Extract BNS / IPC / CrPC / BNSS / BSA section references from the document text."""
    patterns = [
        r'(?:BNS|Bharatiya Nyaya Sanhita)\s*(?:Section|Sec\.?|S\.)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:IPC|Indian Penal Code)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:CrPC|BNSS|Bharatiya Nagarik Suraksha Sanhita)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:BSA|Bharatiya Sakshya Adhiniyam)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'[Ss]ection\s*\d+(?:\s*\([^)]+\))?\s+(?:of\s+(?:the\s+)?)?(?:BNS|IPC|CrPC|BNSS|BSA|Indian Penal Code|Bharatiya Nyaya Sanhita)',
        r'[Uu]/[Ss]\s*\d+(?:\s*\([^)]+\))?',   # shorthand u/s 420
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            s = m.group(0).strip()
            if len(s) > 4:
                found.add(s)
    return sorted(found)[:12]


def explain_legal_sections(sections: list[str], doc_type: str) -> list[dict]:
    """Return plain-English explanations for each section using Groq."""
    if not sections:
        return []
    slist = "\n".join(f"- {s}" for s in sections[:8])
    prompt = (
        f"You are an expert in Indian law (IPC, BNS 2023, CrPC, BNSS 2023, BSA 2023).\n"
        f"A {doc_type} mentions these legal provisions. Explain each one for a non-lawyer.\n\n"
        f"SECTIONS:\n{slist}\n\n"
        "Return a JSON array:\n"
        '[{\n'
        '  "section": "BNS Section 304",\n'
        '  "title": "Theft",\n'
        '  "explanation": "Punishes taking someone else\'s property without consent with dishonest intent.",\n'
        '  "punishment": "Imprisonment up to 3 years, or fine, or both",\n'
        '  "key_elements": ["Dishonest intention", "Property belongs to another", "Without consent"]\n'
        "}]\n\n"
        "Be accurate about BNS 2023 sections. Return ONLY valid JSON array."
    )
    raw  = call_llm(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    return data if isinstance(data, list) else []


# ─────────────────────────────────────────────────────────────
# IndianKanoon
# ─────────────────────────────────────────────────────────────
def fetch_case_laws(query: str, doc_type: str, sections: list[str] = None) -> list[dict]:
    """Fetch case laws — searches each legal section first, then falls back to general query."""
    if not INDIANKANOON_API_KEY:
        return [{
            "title":   "IndianKanoon API key not configured",
            "summary": "Add INDIANKANOON_API_KEY to your .env file.",
            "url":     "https://indiankanoon.org",
            "court":   "", "year": "", "related_section": None,
        }]

    # Build targeted queries — specific section searches first
    queries: list[str] = []
    if sections:
        for s in sections[:5]:
            queries.append(s)
    queries.append(query[:200])   # general fallback

    results, seen_tids = [], set()
    for search_q in queries:
        if len(results) >= 6:
            break
        try:
            r = req.post(
                "https://api.indiankanoon.org/search/",
                data={"formInput": search_q, "pagenum": 0},
                headers={"Authorization": f"Token {INDIANKANOON_API_KEY}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            r.raise_for_status()
            for doc in r.json().get("docs", [])[:3]:
                tid = doc.get("tid", "")
                if tid in seen_tids:
                    continue
                seen_tids.add(tid)
                summary = call_llm(
                    f"Summarize this Indian court judgment in 2-3 plain English sentences "
                    f"relevant to '{search_q}':\n{doc.get('headline','')} {doc.get('doc','')[:500]}\n"
                    "Write only the summary.",
                    temperature=0.1,
                )
                results.append({
                    "title":           doc.get("title", "Untitled"),
                    "summary":         summary,
                    "url":             f"https://indiankanoon.org/doc/{tid}",
                    "court":           doc.get("docsource", ""),
                    "year":            doc.get("publishdate", "")[:4] if doc.get("publishdate") else "",
                    "related_section": search_q if (sections and search_q in sections) else None,
                })
        except Exception as e:
            print(f"[KANOON] Error for '{search_q[:60]}': {e}")
    return results



# ─────────────────────────────────────────────────────────────
# Document RAG — multi-turn Q&A  (ENHANCED)
# ─────────────────────────────────────────────────────────────
class DocumentRAG:
    """In-memory vector store for a single uploaded document. Supports multi-turn conversation."""

    def __init__(self):
        self.embedder   = SentenceTransformer(EMBED_MODEL, device=str(DEVICE))
        self.chunks:     list[str]  = []
        self.embeddings             = []
        self.doc_type:   str        = "Legal Document"
        # Multi-turn: store full conversation history
        self.history:    list[dict] = []   # [{"role": "user"/"assistant", "content": "..."}]

    def index(self, clauses: list[str], doc_type: str = "Legal Document"):
        self.chunks     = clauses
        self.doc_type   = doc_type
        self.embeddings = self.embedder.encode(
            clauses, normalize_embeddings=True, convert_to_numpy=True
        )
        print(f"[DocRAG] Indexed {len(clauses)} chunks for {doc_type}")

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        if not self.chunks:
            return []
        import numpy as np
        q_emb   = self.embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores  = (self.embeddings @ q_emb.T).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.chunks[i] for i in top_idx]

    def answer(self, question: str) -> QAResponse:
        """Bulletproof multi-turn Q&A with legal expert system prompt."""
        print(f"[DocRAG.answer] Q: {question[:100]}")
        if not self.chunks:
            return QAResponse(question=question,
                answer="No document indexed. Please upload a document first.",
                confidence=0.0, sources=[], disclaimer="Upload a document to begin.")

        # Top-6 relevant chunks + always include opening paragraph for context
        relevant = self.retrieve(question, top_k=6)
        if self.chunks and self.chunks[0] not in relevant:
            relevant = [self.chunks[0]] + relevant[:5]
        context = "\n\n---\n\n".join(relevant)

        system_prompt = (
            f"You are NyayaBot, an elite Indian legal analyst with deep expertise in:\n"
            f"- Bharatiya Nyaya Sanhita (BNS) 2023 & Indian Penal Code (IPC) 1860\n"
            f"- BNSS 2023 & CrPC | Bharatiya Sakshya Adhiniyam (BSA) 2023\n"
            f"- FIR procedure, bail, arrest, trial, constitutional rights (Articles 20-22)\n\n"
            f"You are analysing a {self.doc_type}. Answer ONLY from the document below.\n\n"
            f"DOCUMENT CONTENT:\n{context}\n\n"
            "RULES (strictly follow):\n"
            "1. Base every answer strictly on the document. If not mentioned, say so explicitly.\n"
            "2. For follow-up / cross-questions, use conversation history for continuity.\n"
            "3. Cite specific sections, names, dates, or clause text from the document.\n"
            "4. Define any legal term in plain language immediately after using it.\n"
            "5. Never speculate or hallucinate facts not present in the document."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in self.history[-10:]:
            messages.append(turn)
        messages.append({"role": "user", "content": question})

        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=2000,
            )
            answer_text = resp.choices[0].message.content.strip()
            self.history.append({"role": "user",      "content": question})
            self.history.append({"role": "assistant", "content": answer_text})
            confidence = compute_confidence(context, answer_text)
            disclaimer = ""
            if confidence < 0.4:
                disclaimer = "⚠ Low confidence — verify with the document or consult a lawyer."
            elif confidence < 0.65:
                disclaimer = "ℹ Moderate confidence — cross-check with the original document."
            return QAResponse(question=question, answer=answer_text, confidence=confidence,
                sources=[c[:120] for c in relevant[:3]], disclaimer=disclaimer)
        except Exception as e:
            print(f"[DocRAG.answer] Error: {e}")
            return QAResponse(question=question, answer=f"Error: {str(e)}",
                confidence=0.0, sources=[], disclaimer="Technical error. Please try again.")

# ─────────────────────────────────────────────────────────────
# Main analysis pipeline
# ─────────────────────────────────────────────────────────────
def analyze_document(
    file_bytes:    bytes,
    filename:      str,
    max_clauses:   int = 15,
    type_override: Optional[str] = None,
) -> tuple[DocumentAnalysis, DocumentRAG]:

    print(f"\n[ANALYZER] Processing: {filename}")

    # 1. Extract text
    text = extract_text(file_bytes, filename)
    if not text:
        raise ValueError("Could not extract text from document.")
    print(f"[ANALYZER] Extracted {len(text)} chars")

    # 1.5. Auto-translate if regional language
    lang_info        = detect_language_with_llm(text)
    source_lang_code = lang_info.get("language_code", "en")
    source_lang_name = lang_info.get("language_name", "English")

    original_text          = None
    full_translation       = None
    translation_engine     = None
    translation_confidence = None

    if source_lang_code != "en":
        print(f"[ANALYZER] Detected {source_lang_name}. Translating via Google Gemini...")
        tr = translate_legal_text(text, source_lang=source_lang_code, target_lang="en")
        if tr.get("translated_text"):
            original_text          = text
            full_translation       = tr["translated_text"]
            text                   = full_translation
            translation_engine     = tr.get("engine", "unknown")
            translation_confidence = tr.get("confidence")
            print(f"[ANALYZER] Translation done ({translation_engine}).")
        else:
            print("[ANALYZER] Translation failed. Using original.")
            source_lang_name = "English (Fallback)"

    # 1.6. Extract legal section references (BNS, IPC, CrPC …)
    combined_text      = text + (" " + original_text if original_text else "")
    mentioned_sections = extract_legal_sections(combined_text)
    print(f"[ANALYZER] Sections found: {mentioned_sections}")

    # 2. Document type
    if type_override and type_override in DOCUMENT_TYPES:
        type_key, doc_type, type_conf = type_override, DOCUMENT_TYPES[type_override]["label"], 100
    else:
        type_key, doc_type, type_conf = detect_document_type(text)
    print(f"[ANALYZER] Type: {doc_type} ({type_conf}%)")

    # 2.5. Plain-English explanations for every section found
    section_explanations = []
    if mentioned_sections:
        print(f"[ANALYZER] Explaining {len(mentioned_sections)} sections...")
        section_explanations = explain_legal_sections(mentioned_sections, doc_type)

    # 3. Segment + analyse clauses
    all_clauses = segment_clauses(text)
    clauses     = all_clauses[:max_clauses]
    print(f"[ANALYZER] {len(all_clauses)} clauses, analysing {len(clauses)}")

    analyzed: list[ClauseAnalysis] = []
    for i, clause in enumerate(clauses):
        print(f"[ANALYZER] Clause {i+1}/{len(clauses)}...")
        analyzed.append(analyze_clause(clause, doc_type))

    summary = summarize_document(text, doc_type)
    dist    = {"Safe": 0, "Caution": 0, "High Risk": 0, "Illegal": 0}
    for c in analyzed:
        dist[c.risk_level] = dist.get(c.risk_level, 0) + 1
    overall = compute_overall_risk(analyzed)

    try:
        from lex_validator import compute_compliance_score
        comp_score = compute_compliance_score(text)["score"]
    except Exception:
        comp_score = 75

    # 9. Case laws — section-targeted search first
    risky    = [c for c in analyzed if c.risk_level in ["High Risk", "Illegal"]]
    kw_src   = risky or [c for c in analyzed if c.risk_level == "Caution"]
    kws      = [c.explanation[:80] for c in kw_src[:2] if c.explanation and len(c.explanation) > 20]
    kanoon_q = (f"{doc_type} {' '.join(kws)}")[:200] if kws else doc_type
    case_laws = fetch_case_laws(kanoon_q, doc_type, sections=mentioned_sections)

    party_obligations   = extract_party_obligations(text, doc_type)
    missing_clauses     = detect_missing_clauses(text, type_key)
    key_numbers         = extract_key_numbers(text)
    deadlines           = extract_deadlines(text)
    suggested_questions = generate_suggested_questions(text, doc_type)
    signature_verdict   = get_signature_verdict(analyzed, missing_clauses)

    recommendations = []
    if dist["Illegal"] > 0:
        recommendations.append(f"⚠️ {dist['Illegal']} clause(s) may violate Indian law. Do not sign without legal review.")
    if dist["High Risk"] > 0:
        recommendations.append(f"🔴 {dist['High Risk']} high-risk clause(s) found. Negotiate before signing.")
    if dist["Caution"] > 0:
        recommendations.append(f"🟡 {dist['Caution']} clause(s) need attention. Read carefully.")
    if comp_score < 70:
        recommendations.append(f"📋 Document uses obsolete IPC/CrPC references (Score: {comp_score}/100). Request updated version.")
    if not recommendations:
        recommendations.append("✅ Document appears fair. Standard review recommended before signing.")

    doc_rag = DocumentRAG()
    doc_rag.index(all_clauses, doc_type)

    result = DocumentAnalysis(
        document_name=filename,
        document_type=doc_type,
        document_type_key=type_key,
        type_confidence=type_conf,
        total_clauses=len(analyzed),
        summary=summary,
        risk_distribution=dist,
        clauses=analyzed,
        overall_risk=overall,
        compliance_score=comp_score,
        case_laws=case_laws,
        recommendations=recommendations,
        party_obligations=party_obligations,
        missing_clauses=missing_clauses,
        key_numbers=key_numbers,
        deadlines=deadlines,
        suggested_questions=suggested_questions,
        signature_verdict=signature_verdict,
        original_text=original_text,
        source_language=source_lang_name if original_text else None,
        full_translation=full_translation,
        translation_engine=translation_engine,
        translation_confidence=translation_confidence,
        mentioned_sections=mentioned_sections,
        section_explanations=section_explanations,
    )
    print(f"[ANALYZER] Done. Verdict: {signature_verdict.verdict}")
    return result, doc_rag