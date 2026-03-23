"""
lex_validator.py — Lex-Validator Features for Nyaya-Setu
Team IKS | SPIT CSE 2025-26

Four features:
  1. IPC → BNS Migration Checker
  2. Citation Verifier (checks section exists in RAG knowledge base)
  3. Compliance Scorer (0-100)
  4. IRAC Reasoning formatter (used by judge_engine.py)
"""

import os, sys, re, json
sys.path.append(os.path.dirname(__file__))

import fitz          # PyMuPDF — for reading uploaded PDFs
import ollama
from dotenv import load_dotenv

load_dotenv()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# ─────────────────────────────────────────────────────────────────────────────
# 1. IPC → BNS MAPPING TABLE
#    Source: Official Gazette of India, MHA Comparative Statement 2023
# ─────────────────────────────────────────────────────────────────────────────
IPC_TO_BNS = {
    # Offences against body
    "IPC 299":  {"bns": "BNS 99",   "name": "Culpable homicide"},
    "IPC 300":  {"bns": "BNS 100",  "name": "Murder"},
    "IPC 302":  {"bns": "BNS 101",  "name": "Punishment for murder"},
    "IPC 304":  {"bns": "BNS 105",  "name": "Culpable homicide not amounting to murder"},
    "IPC 304A": {"bns": "BNS 106",  "name": "Death by negligence"},
    "IPC 304B": {"bns": "BNS 80",   "name": "Dowry death"},
    "IPC 306":  {"bns": "BNS 108",  "name": "Abetment of suicide"},
    "IPC 307":  {"bns": "BNS 109",  "name": "Attempt to murder"},
    "IPC 309":  {"bns": "ABOLISHED","name": "Attempt to suicide — ABOLISHED under BNS"},
    "IPC 319":  {"bns": "BNS 114",  "name": "Hurt"},
    "IPC 320":  {"bns": "BNS 116",  "name": "Grievous hurt"},
    "IPC 323":  {"bns": "BNS 115",  "name": "Voluntarily causing hurt"},
    "IPC 324":  {"bns": "BNS 118",  "name": "Voluntarily causing hurt by dangerous weapons"},
    "IPC 325":  {"bns": "BNS 117",  "name": "Voluntarily causing grievous hurt"},
    "IPC 326":  {"bns": "BNS 118",  "name": "Voluntarily causing grievous hurt by dangerous weapons"},
    "IPC 326A": {"bns": "BNS 124",  "name": "Acid attack"},
    "IPC 326B": {"bns": "BNS 125",  "name": "Attempt to throw acid"},
    "IPC 354":  {"bns": "BNS 74",   "name": "Assault with intent to outrage modesty"},
    "IPC 354A": {"bns": "BNS 75",   "name": "Sexual harassment"},
    "IPC 354B": {"bns": "BNS 76",   "name": "Assault with intent to disrobe"},
    "IPC 354C": {"bns": "BNS 77",   "name": "Voyeurism"},
    "IPC 354D": {"bns": "BNS 78",   "name": "Stalking"},
    "IPC 375":  {"bns": "BNS 63",   "name": "Rape"},
    "IPC 376":  {"bns": "BNS 64",   "name": "Punishment for rape"},
    "IPC 376A": {"bns": "BNS 66",   "name": "Rape causing death or vegetative state"},
    "IPC 376D": {"bns": "BNS 70",   "name": "Gang rape"},
    # Offences against property
    "IPC 378":  {"bns": "BNS 303",  "name": "Theft"},
    "IPC 379":  {"bns": "BNS 303",  "name": "Punishment for theft"},
    "IPC 380":  {"bns": "BNS 305",  "name": "Theft in dwelling house"},
    "IPC 382":  {"bns": "BNS 306",  "name": "Theft after preparation for hurt"},
    "IPC 383":  {"bns": "BNS 308",  "name": "Extortion"},
    "IPC 384":  {"bns": "BNS 308",  "name": "Punishment for extortion"},
    "IPC 390":  {"bns": "BNS 309",  "name": "Robbery"},
    "IPC 391":  {"bns": "BNS 310",  "name": "Dacoity"},
    "IPC 392":  {"bns": "BNS 309",  "name": "Punishment for robbery"},
    "IPC 395":  {"bns": "BNS 310",  "name": "Punishment for dacoity"},
    "IPC 397":  {"bns": "BNS 311",  "name": "Robbery with attempt to cause death"},
    "IPC 399":  {"bns": "BNS 312",  "name": "Making preparation to commit dacoity"},
    "IPC 406":  {"bns": "BNS 316",  "name": "Criminal breach of trust"},
    "IPC 415":  {"bns": "BNS 318",  "name": "Cheating"},
    "IPC 416":  {"bns": "BNS 319",  "name": "Cheating by impersonation"},
    "IPC 417":  {"bns": "BNS 318",  "name": "Punishment for cheating"},
    "IPC 420":  {"bns": "BNS 318",  "name": "Cheating and dishonestly inducing delivery"},
    "IPC 425":  {"bns": "BNS 324",  "name": "Mischief"},
    "IPC 426":  {"bns": "BNS 324",  "name": "Punishment for mischief"},
    "IPC 427":  {"bns": "BNS 324",  "name": "Mischief causing damage"},
    "IPC 441":  {"bns": "BNS 329",  "name": "Criminal trespass"},
    "IPC 442":  {"bns": "BNS 330",  "name": "House trespass"},
    "IPC 447":  {"bns": "BNS 329",  "name": "Punishment for criminal trespass"},
    "IPC 448":  {"bns": "BNS 330",  "name": "Punishment for house trespass"},
    # Public order
    "IPC 499":  {"bns": "BNS 356",  "name": "Defamation"},
    "IPC 500":  {"bns": "BNS 356",  "name": "Punishment for defamation"},
    "IPC 503":  {"bns": "BNS 351",  "name": "Criminal intimidation"},
    "IPC 504":  {"bns": "BNS 352",  "name": "Intentional insult to provoke breach of peace"},
    "IPC 506":  {"bns": "BNS 351",  "name": "Punishment for criminal intimidation"},
    "IPC 509":  {"bns": "BNS 79",   "name": "Word/gesture intended to insult modesty"},
    # Domestic violence
    "IPC 498A": {"bns": "BNS 85",   "name": "Cruelty by husband or relatives"},
    "IPC 304B": {"bns": "BNS 80",   "name": "Dowry death"},
    # Wrongful confinement
    "IPC 339":  {"bns": "BNS 126",  "name": "Wrongful restraint"},
    "IPC 340":  {"bns": "BNS 127",  "name": "Wrongful confinement"},
    "IPC 341":  {"bns": "BNS 126",  "name": "Punishment for wrongful restraint"},
    "IPC 342":  {"bns": "BNS 127",  "name": "Punishment for wrongful confinement"},
    # CrPC → BNSS common references
    "CrPC 154": {"bns": "BNSS 173", "name": "FIR registration"},
    "CrPC 156": {"bns": "BNSS 175", "name": "Police investigation"},
    "CrPC 161": {"bns": "BNSS 180", "name": "Examination of witnesses by police"},
    "CrPC 164": {"bns": "BNSS 183", "name": "Recording of confessions and statements"},
    "CrPC 167": {"bns": "BNSS 187", "name": "Remand"},
    "CrPC 173": {"bns": "BNSS 193", "name": "Report of police officer on completion of investigation"},
    "CrPC 197": {"bns": "BNSS 218", "name": "Prosecution of judges and public servants"},
    "CrPC 313": {"bns": "BNSS 351", "name": "Power to examine the accused"},
    "CrPC 437": {"bns": "BNSS 479", "name": "Bail in non-bailable offences"},
    "CrPC 438": {"bns": "BNSS 482", "name": "Anticipatory bail"},
    "CrPC 439": {"bns": "BNSS 483", "name": "Special powers of Sessions Court re bail"},
    # Evidence Act → BSA
    "IEA 65B":  {"bns": "BSA 63",   "name": "Electronic evidence admissibility"},
    "IEA 27":   {"bns": "BSA 23",   "name": "Admissibility of confession to police"},
}

# Aliases for flexible matching
IPC_ALIASES = {}
for key in IPC_TO_BNS:
    # "IPC 420" → also match "Section 420", "Sec 420", "420 IPC"
    num = key.split()[-1]
    act = key.split()[0]
    IPC_ALIASES[f"Section {num}"] = key
    IPC_ALIASES[f"Sec {num}"]     = key
    IPC_ALIASES[f"{num} {act}"]   = key
    IPC_ALIASES[f"s.{num}"]       = key


# ─────────────────────────────────────────────────────────────────────────────
# 2. IPC → BNS MIGRATION CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def check_ipc_references(text: str) -> dict:
    """
    Scan text for IPC/CrPC/IEA references.
    Returns migration report.
    """

    import re

    found    = []
    obsolete = []
    migrated = []

    patterns = [
        # IPC patterns
        r'\bIPC\s+(\d+[A-Z]?)\b',
        r'\bSection\s+(\d+[A-Z]?)\s+IPC\b',
        r'\bSections?\s+([\d,\sand()]+)\s+(?:of\s+the\s+)?IPC\b',
        r'\bS\.\s*(\d+[A-Z]?)\s+IPC\b',

        # CrPC patterns
        r'\bCrPC\s+(\d+[A-Z]?(?:\(\d+\))?)\b',
        r'\bSection\s+(\d+[A-Z]?(?:\(\d+\))?)\s+(?:of\s+)?CrPC\b',

        # Evidence Act
        r'\bIEA\s+(\d+[A-Z]?)\b',
        r'\bSection\s+65B\b',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for m in matches:

            # 🔥 HANDLE MULTIPLE SECTIONS
            if isinstance(m, str):
                cleaned = m.replace("and", ",")
                cleaned = cleaned.replace(" ", "")
                parts = cleaned.split(",")
            else:
                parts = [m]

            for part in parts:
                if not part:
                    continue

                # 🔥 REMOVE (3) → for CrPC 156(3)
                base_part = re.sub(r'\(\d+\)', '', part)

                # 🔥 DETERMINE ACT
                if 'CrPC' in pattern:
                    key = f"CrPC {base_part}"
                elif 'IEA' in pattern or '65B' in pattern:
                    key = f"IEA {base_part}"
                else:
                    key = f"IPC {base_part}"

                # 🔥 AVOID DUPLICATES
                if key in [f["old"] for f in found]:
                    continue

                mapping = IPC_TO_BNS.get(key)

                if mapping:
                    found.append({
                        "old":  key,
                        "new":  mapping["bns"],
                        "name": mapping["name"],
                    })

                    if mapping["bns"] == "ABOLISHED":
                        obsolete.append(key)
                    else:
                        migrated.append(key)

    return {
        "total_old_references": len(found),
        "migrated": migrated,
        "obsolete": obsolete,
        "mappings": found,
    }

def compute_compliance_score(text: str) -> dict:
    """
    Compute 0-100 BNS compliance score for a legal document.
    100 = fully BNS/BNSS/BSA compliant
    0   = entirely IPC/CrPC/IEA based
    """
    report = check_ipc_references(text)

    # Count BNS references already in document
    bns_refs  = len(re.findall(r'\bBNS\s+\d+\b', text, re.IGNORECASE))
    bnss_refs = len(re.findall(r'\bBNSS\s+\d+\b', text, re.IGNORECASE))
    bsa_refs  = len(re.findall(r'\bBSA\s+\d+\b', text, re.IGNORECASE))
    new_refs  = bns_refs + bnss_refs + bsa_refs

    old_refs  = report["total_old_references"]
    total     = old_refs + new_refs

    if total == 0:
        score = 100   # No statutory references at all — technically compliant
        note  = "No statutory references found in document."
    elif old_refs == 0:
        score = 100
        note  = "Document uses only BNS/BNSS/BSA references. Fully compliant."
    else:
        # Penalise for each old reference; extra penalty for ABOLISHED sections
        abolished_count = len(report["obsolete"])
        base_score = int((new_refs / total) * 100)
        penalty    = abolished_count * 5
        score      = max(0, base_score - penalty)
        note       = (
            f"{old_refs} obsolete IPC/CrPC references found. "
            f"{new_refs} BNS/BNSS/BSA references found. "
            f"{abolished_count} abolished sections cited."
        )

    return {
        "score":    score,
        "grade":    "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "F",
        "note":     note,
        "report":   report,
    }


def generate_migration_message(result: dict) -> str:
    """Format migration result as a clean WhatsApp message."""
    score    = result["score"]
    grade    = result["grade"]
    note     = result["note"]
    mappings = result["report"]["mappings"]
    obsolete = result["report"]["obsolete"]

    # Score bar
    filled = int(score / 10)
    bar    = "█" * filled + "░" * (10 - filled)

    msg = (
        f"📋 BNS Compliance Score\n\n"
        f"{bar} {score}/100 (Grade {grade})\n\n"
        f"{note}\n"
    )

    if mappings:
        msg += "\n🔄 IPC → BNS Corrections:\n"
        for m in mappings[:8]:  # max 8 to keep WhatsApp message short
            if m["new"] == "ABOLISHED":
                msg += f"❌ {m['old']} → ABOLISHED under BNS\n   ({m['name']})\n"
            else:
                msg += f"✅ {m['old']} → {m['new']}\n   ({m['name']})\n"

    if obsolete:
        msg += (
            f"\n⚠️ Warning: {len(obsolete)} abolished section(s) cited.\n"
            f"These offences no longer exist under BNS 2023.\n"
        )

    if score < 70:
        msg += (
            "\n📌 Action required: Update all IPC/CrPC references to BNS/BNSS "
            "before filing. Courts may reject documents citing obsolete sections."
        )
    else:
        msg += "\n✅ Document is largely BNS-compliant."

    return msg


# ─────────────────────────────────────────────────────────────────────────────
# 3. CITATION VERIFIER
#    Checks that sections cited by judge_engine actually exist in legal_kb.json
# ─────────────────────────────────────────────────────────────────────────────
KB_PATH = os.path.join(os.path.dirname(__file__), "data", "legal_kb.json")

def load_kb_sections() -> set[str]:
    """Load all known BNS section numbers from the knowledge base."""
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            kb = json.load(f)
        sections = set()
        for offence in kb["offences"]:
            # Extract section numbers from strings like "BNS Section 303(2)"
            nums = re.findall(r'(?:BNS|BNSS|BSA)\s+(?:Section\s+)?(\d+[A-Z]?(?:\(\d+\))?)', 
                            offence["bns_section"])
            for n in nums:
                sections.add(n)
        return sections
    except Exception:
        return set()

KNOWN_SECTIONS = load_kb_sections()

def verify_citations(sections: list[str]) -> dict:
    """
    Verify that cited sections are in the knowledge base.
    Returns verification result with any suspicious citations flagged.
    """
    verified   = []
    unverified = []

    for section in sections:
        # Extract number from "BNS Section 303" or "BNS 303"
        nums = re.findall(r'(\d+[A-Z]?(?:\(\d+\))?)', section)
        if any(n in KNOWN_SECTIONS for n in nums):
            verified.append(section)
        else:
            unverified.append(section)

    return {
        "verified":        verified,
        "unverified":      unverified,
        "all_verified":    len(unverified) == 0,
        "confidence":      "High" if len(unverified) == 0 else "Medium" if len(verified) > 0 else "Low",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. IRAC REASONING FORMATTER
#    Formats a case judgement using IRAC structure via Llama-3
# ─────────────────────────────────────────────────────────────────────────────
def format_irac(
    complaint:    str,
    section:      str,
    section_desc: str,
    punishment:   str,
    case_facts:   str,
) -> str:
    """
    Generate IRAC-structured legal reasoning for a case.
    IRAC = Issue → Rule → Application → Conclusion
    """
    prompt = f"""You are a senior Indian legal advocate. 
Analyse this case using the IRAC framework. Keep each section SHORT — 2-3 sentences maximum.
Use simple English. No jargon.

CASE FACTS: {case_facts}
COMPLAINT: {complaint}
APPLICABLE SECTION: {section}
SECTION DESCRIPTION: {section_desc}
PUNISHMENT: {punishment}

Respond in exactly this format — nothing else:

ISSUE
[What is the precise legal question? What wrong was committed?]

RULE
[What does {section} say? What are the legal elements that must be proven?]

APPLICATION
[How do the facts of this case satisfy or not satisfy the rule? Is the case strong or weak?]

CONCLUSION
[What is the likely legal outcome? What should the complainant do?]"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2, "num_ctx": 2048, "num_gpu": 99},
    )
    return response["message"]["content"].strip()


# ─────────────────────────────────────────────────────────────────────────────
# 5. PDF TEXT EXTRACTOR (for document uploads)
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from a PDF uploaded by the user."""
    try:
        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        return f"ERROR: Could not read PDF — {e}"


def extract_text_from_image_bytes(img_bytes: bytes) -> str:
    """
    Extract text from an image (photo of a legal document) using PyMuPDF.
    Note: For better OCR use pytesseract if installed.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
        img  = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        return "OCR not available. Please upload a PDF version of the document."
    except Exception as e:
        return f"ERROR: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# CLI TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== TEST 1: IPC → BNS Migration ===")
    sample = """
    The accused is charged under IPC 420 for cheating and IPC 506 for criminal 
    intimidation. The complainant also invokes IPC 354 for assault on modesty.
    The case was filed under CrPC 154 and the evidence was collected under IEA 65B.
    Additionally IPC 309 (attempt to suicide) was cited by the defense.
    """
    result = compute_compliance_score(sample)
    print(f"Score: {result['score']}/100 (Grade {result['grade']})")
    print(f"Note: {result['note']}")
    print("\nMappings:")
    for m in result["report"]["mappings"]:
        print(f"  {m['old']} → {m['new']} ({m['name']})")
    print("\nWhatsApp message preview:")
    print(generate_migration_message(result))

    print("\n=== TEST 2: Citation Verifier ===")
    sections = ["BNS Section 304", "BNS Section 303", "BNS Section 999", "BNSS Section 175"]
    v = verify_citations(sections)
    print(f"Verified: {v['verified']}")
    print(f"Unverified: {v['unverified']}")
    print(f"Confidence: {v['confidence']}")

    print("\n=== TEST 3: IRAC Reasoning ===")
    irac = format_irac(
        complaint="Sarang snatched my phone near Andheri station",
        section="BNS Section 304",
        section_desc="Snatching — suddenly taking property from a person",
        punishment="Up to 3 years imprisonment + fine",
        case_facts="Accused grabbed complainant's phone and fled on a bike. No injury. No witnesses. Incident near Andheri station.",
    )
    print(irac)