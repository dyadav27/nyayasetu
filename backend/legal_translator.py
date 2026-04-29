"""
legal_translator.py — Legal Document Translation for Nyaya-Setu
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Translation Engine : Sarvam AI  (powered by IndicTrans2 — same model, cloud-hosted, free credits)
Language Detection : Groq  (Llama 3.3 70B — cheap, ~100 tokens)
Legal Term Analysis: Groq  (post-translation extraction)
Fallback           : Groq full translation (if Sarvam key missing / API down)

Supports: Marathi, Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati,
           Malayalam, Punjabi, Odia, Assamese, Urdu
"""

import os, re, json, requests
from groq import Groq
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ── Clients & config ──────────────────────────────────────────────────────────
groq_client      = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ── Language tables ───────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "mr": "Marathi",   "hi": "Hindi",     "ta": "Tamil",
    "te": "Telugu",    "kn": "Kannada",   "bn": "Bengali",
    "gu": "Gujarati",  "ml": "Malayalam", "pa": "Punjabi",
    "or": "Odia",      "as": "Assamese",  "ur": "Urdu",
    "en": "English",
}

# ISO 639-1 → Gemini language names
GEMINI_LANGS = {
    "mr": "Marathi", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati", "ml": "Malayalam",
    "pa": "Punjabi", "or": "Odia", "as": "Assamese", "ur": "Urdu",
    "en": "English",
}

# Unicode ranges for script-based fallback detection
SCRIPT_RANGES = {
    "mr": [(0x0900, 0x097F)],
    "hi": [(0x0900, 0x097F)],
    "ta": [(0x0B80, 0x0BFF)],
    "te": [(0x0C00, 0x0C7F)],
    "kn": [(0x0C80, 0x0CFF)],
    "bn": [(0x0980, 0x09FF)],
    "gu": [(0x0A80, 0x0AFF)],
    "ml": [(0x0D00, 0x0D7F)],
    "pa": [(0x0A00, 0x0A7F)],
    "or": [(0x0B00, 0x0B7F)],
    "as": [(0x0980, 0x09FF)],
    "ur": [(0x0600, 0x06FF), (0xFB50, 0xFDFF)],
}


# ── Language detection ────────────────────────────────────────────────────────
def detect_script(text: str) -> str:
    """Unicode-range based script detection. Returns ISO 639-1 code."""
    counts = {}
    for ch in text:
        cp = ord(ch)
        for lang, ranges in SCRIPT_RANGES.items():
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    counts[lang] = counts.get(lang, 0) + 1
                    break
    return max(counts, key=counts.get) if counts else "en"


def detect_language_with_llm(text: str) -> dict:
    """Use Groq LLM to precisely identify language (Hindi vs Marathi etc.)."""
    sample = text[:500]
    prompt = (
        "Identify the language of this Indian legal document text.\n"
        "Reply with ONLY a JSON object, no other text.\n\n"
        f"TEXT:\n{sample}\n\n"
        'JSON format: {"language_code": "mr", "language_name": "Marathi", "confidence": 95}\n\n'
        "Codes: mr=Marathi, hi=Hindi, ta=Tamil, te=Telugu, kn=Kannada, "
        "bn=Bengali, gu=Gujarati, ml=Malayalam, pa=Punjabi, or=Odia, "
        "as=Assamese, ur=Urdu, en=English"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100,
        )
        raw = resp.choices[0].message.content.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        print(f"[TRANSLATOR] LLM language detection failed: {e}")

    code = detect_script(text)
    return {
        "language_code": code,
        "language_name": SUPPORTED_LANGUAGES.get(code, "Unknown"),
        "confidence": 60,
    }


# ── Gemini translation ────────────────────────────────────────────────────────
def _gemini_translate(text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
    """
    Translate using Google Gemini API. Handles large documents well.
    Returns (translated_text, confidence 0-100).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    src_name = GEMINI_LANGS.get(src_lang, src_lang)
    tgt_name = GEMINI_LANGS.get(tgt_lang, tgt_lang)
    
    print(f"[TRANSLATOR] Gemini: Translating {len(text)} chars from {src_name} to {tgt_name}...")
    
    # Using Gemini 2.5 Flash for the best high-fidelity translation
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = (
        f"You are a highly accurate legal translator. Translate the following First Information Report (FIR) / legal document from {src_name} to {tgt_name}.\n"
        "Rules:\n"
        "1. Preserve all proper nouns, names, dates, and locations accurately without hallucinating.\n"
        "2. Preserve all section numbers and act names precisely.\n"
        "3. Maintain the formal legal tone of the original.\n"
        "4. Output ONLY the translated text without any conversational filler or commentary.\n\n"
        f"SOURCE TEXT ({src_name}):\n{text}"
    )
    
    try:
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        if not translated_text:
            raise ValueError("Gemini returned empty translation.")
        return translated_text, 95.0
    except Exception as e:
        print(f"[TRANSLATOR] Gemini API error: {e}")
        raise ValueError(f"Gemini translation failed: {e}")




# ── Legal term extraction (post-translation) ──────────────────────────────────
def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into chunks at sentence/newline boundaries."""
    # Try splitting on newlines first, then on sentence endings
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single line is too long, split on sentence boundaries
            if len(line) > max_chars:
                sentences = re.split(r'(?<=[।.!?])\s+', line)
                current = ""
                for sent in sentences:
                    trial = (current + " " + sent).strip() if current else sent
                    if len(trial) <= max_chars:
                        current = trial
                    else:
                        if current:
                            chunks.append(current)
                        current = sent[:max_chars]  # hard cut last resort
            else:
                current = line
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]

def _extract_legal_terms(original: str, translated: str, src_name: str) -> list[str]:
    """
    After Sarvam has translated, ask Groq to identify key legal terms
    that were preserved or translated in the English output.
    Cheap call — only looks at up to 1500 chars.
    """
    sample_orig  = original[:800]
    sample_trans = translated[:800]
    prompt = (
        f"You are a legal analyst. Given this {src_name} → English translation of a legal document, "
        "list the key legal terms that appear in the English translation. "
        "Include section numbers, act names, legal roles (Complainant, Accused, etc.), and legal procedures.\n\n"
        f"ORIGINAL ({src_name}):\n{sample_orig}\n\n"
        f"ENGLISH TRANSLATION:\n{sample_trans}\n\n"
        'Reply with ONLY a JSON array of strings, e.g. ["Section 302", "Bharatiya Nyaya Sanhita", "Complainant"]'
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        print(f"[TRANSLATOR] Legal term extraction failed: {e}")
    return []


# ── Groq fallback translation ─────────────────────────────────────────────────
def _groq_translate(text: str, src_name: str, tgt_name: str, document_type: str) -> tuple[str, float]:
    """Full translation via Groq LLM — used only as fallback."""
    MAX_CHARS = 6000
    if len(text) > MAX_CHARS:
        # Chunk for Groq too
        chunks = _split_into_chunks(text, MAX_CHARS)
        parts = []
        min_conf = 100.0
        for chunk in chunks:
            t, c = _groq_translate(chunk, src_name, tgt_name, document_type)
            parts.append(t)
            min_conf = min(min_conf, c)
        return "\n\n".join(parts), min_conf

    prompt = (
        f"Translate the following {document_type} from {src_name} to {tgt_name}.\n"
        "Preserve all legal terms, section numbers, act names, and proper nouns.\n"
        "Output ONLY the translated text, no explanations.\n\n"
        f"SOURCE TEXT:\n{text}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=8000,
        )
        translated = resp.choices[0].message.content.strip()
        return translated, 75.0
    except Exception as e:
        print(f"[TRANSLATOR] Groq fallback failed: {e}")
        return "", 0.0


# ── Core public function ──────────────────────────────────────────────────────
def translate_legal_text(
    text: str,
    source_lang: str = None,
    target_lang: str = "en",
    document_type: str = "FIR / Police Complaint",
) -> dict:
    """
    Translate legal text using Sarvam AI (IndicTrans2) with Groq fallback.

    Args:
        text:          Text to translate
        source_lang:   ISO 639-1 source language code (auto-detected if None)
        target_lang:   ISO 639-1 target language code (default: 'en')
        document_type: Document type for context

    Returns dict with: translated_text, source_language, source_language_name,
                       target_language, target_language_name,
                       legal_terms_preserved, confidence, detection_confidence, notes
    """
    if not text or not text.strip():
        return _error_result("", "en", "Empty text provided.")

    # ── Step 1: Language detection ─────────────────────────────────────────────
    if not source_lang or source_lang == "auto":
        detection = detect_language_with_llm(text)
        source_lang = detection["language_code"]
        detected_name = detection["language_name"]
        detection_confidence = detection.get("confidence", 60)
    else:
        detected_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        detection_confidence = 100

    # Already in target language
    if source_lang == target_lang:
        return {
            "translated_text":       text,
            "source_language":       source_lang,
            "source_language_name":  detected_name,
            "target_language":       target_lang,
            "target_language_name":  SUPPORTED_LANGUAGES.get(target_lang, target_lang),
            "legal_terms_preserved": [],
            "confidence":            100,
            "detection_confidence":  detection_confidence,
            "notes":                 "Text is already in the target language.",
            "engine":                "none",
        }

    src_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
    tgt_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    # ── Step 2: Translate via Google Gemini ───────────────────────────────────
    engine = "gemini-2.5-flash"
    notes  = f"Translated using Google Gemini · {src_name} → {tgt_name}"
    try:
        translated_text, confidence = _gemini_translate(text, source_lang, target_lang)
        print(f"[TRANSLATOR] Gemini OK — {len(translated_text)} chars translated")

    except Exception as e:
        print(f"[TRANSLATOR] Gemini failed ({e}), falling back to Groq...")
        engine = "groq-llm-fallback"
        notes  = f"Gemini unavailable — used Groq LLM fallback · {src_name} → {tgt_name}"
        translated_text, confidence = _groq_translate(text, src_name, tgt_name, document_type)
        if not translated_text:
            return _error_result(source_lang, target_lang, f"Both Gemini and Groq failed: {e}")

    # ── Step 3: Extract legal terms (Groq, post-processing) ───────────────────
    legal_terms = _extract_legal_terms(text, translated_text, src_name)

    return {
        "translated_text":       translated_text,
        "source_language":       source_lang,
        "source_language_name":  src_name,
        "target_language":       target_lang,
        "target_language_name":  tgt_name,
        "legal_terms_preserved": legal_terms,
        "confidence":            confidence,
        "detection_confidence":  detection_confidence,
        "notes":                 notes,
        "engine":                engine,
    }


def _error_result(source_lang: str, target_lang: str, msg: str) -> dict:
    return {
        "translated_text":       "",
        "source_language":       source_lang,
        "source_language_name":  SUPPORTED_LANGUAGES.get(source_lang, source_lang),
        "target_language":       target_lang,
        "target_language_name":  SUPPORTED_LANGUAGES.get(target_lang, target_lang),
        "legal_terms_preserved": [],
        "confidence":            0,
        "detection_confidence":  0,
        "notes":                 msg,
        "engine":                "error",
        "error":                 msg,
    }


# ── Convenience wrappers (public API — unchanged signatures) ──────────────────
def translate_fir(text: str, source_lang: str = None) -> dict:
    """Convenience function specifically for FIR translation."""
    return translate_legal_text(
        text=text,
        source_lang=source_lang,
        document_type="FIR / First Information Report (Police Complaint)",
    )


def get_supported_languages() -> list[dict]:
    """Return list of supported languages for the frontend dropdown."""
    return [
        {"code": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
        if code != "en"
    ]


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_marathi = """
    प्रथम खबर अहवाल (FIR)
    पोलीस ठाणे: अंधेरी पूर्व, मुंबई

    फिर्यादी: श्री. राजेश पाटील, वय ३५ वर्षे
    पत्ता: फ्लॅट नं. ४०२, साई अपार्टमेंट, अंधेरी पूर्व

    आरोपी: अज्ञात व्यक्ती (२ जण)

    घटनेचा तपशील:
    दिनांक १५/०३/२०२५ रोजी रात्री ९:३० वाजता मी अंधेरी स्टेशन जवळून
    चालत जात असताना दोन अज्ञात व्यक्तींनी माझा मोबाईल फोन (Samsung Galaxy S24,
    किंमत ₹७९,९९९) हिसकावून घेतला आणि बाईकवरून पळून गेले.

    कलम: भारतीय न्याय संहिता (BNS) कलम ३०४ — चोरी
    """

    print("Testing legal translation (Marathi → English) via Sarvam AI...")
    result = translate_fir(sample_marathi)
    print(f"\n{'='*60}")
    print(f"Engine    : {result['engine']}")
    print(f"Source    : {result['source_language_name']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nTranslated text:\n{result['translated_text']}")
    print(f"\nLegal terms: {result['legal_terms_preserved']}")
    print(f"Notes: {result['notes']}")
