# -*- coding: utf-8 -*-
"""
local_models.py — Singleton loader for all local HuggingFace models
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Models in hf_models/:
  nllb_model / nllb_tokenizer     → NLLB-200 translation (Hindi/Marathi → English)
  bart_model / bart_tokenizer     → BART summarization (English document summary)
  embedding_model / muril_tokenizer → MuRIL multilingual embeddings (RAG)

All models are loaded lazily (on first use) and cached as singletons.
GPU is used automatically when available; falls back to CPU gracefully.
"""

import os
import torch
from pathlib import Path

# ── Project root & model paths ─────────────────────────────────────────────────
_PROJECT_ROOT  = Path(__file__).resolve().parent.parent
HF_MODELS_DIR  = _PROJECT_ROOT / "hf_models"

NLLB_MODEL_DIR      = str(HF_MODELS_DIR / "nllb_model")
NLLB_TOKENIZER_DIR  = str(HF_MODELS_DIR / "nllb_tokenizer")
BART_MODEL_DIR      = str(HF_MODELS_DIR / "bart_model")
BART_TOKENIZER_DIR  = str(HF_MODELS_DIR / "bart_tokenizer")
EMBED_MODEL_DIR     = str(HF_MODELS_DIR / "embedding_model")
MURIL_TOKENIZER_DIR = str(HF_MODELS_DIR / "muril_tokenizer")

# ── Device ─────────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[LOCAL_MODELS] Using device: {DEVICE}")

# ── NLLB language codes ────────────────────────────────────────────────────────
# Maps ISO 639-1 → NLLB flores-200 language tag
NLLB_LANG_MAP = {
    "hi": "hin_Deva",   # Hindi
    "mr": "mar_Deva",   # Marathi
    "ta": "tam_Taml",   # Tamil
    "te": "tel_Telu",   # Telugu
    "kn": "kan_Knda",   # Kannada
    "bn": "ben_Beng",   # Bengali
    "gu": "guj_Gujr",   # Gujarati
    "ml": "mal_Mlym",   # Malayalam
    "pa": "pan_Guru",   # Punjabi (Gurmukhi)
    "or": "ory_Orya",   # Odia
    "as": "asm_Beng",   # Assamese
    "ur": "urd_Arab",   # Urdu
    "en": "eng_Latn",   # English
}

# ── Singleton instances ────────────────────────────────────────────────────────
_nllb_model        = None
_nllb_tokenizer    = None
_nllb_load_failed  = False   # True after first load error → skip retries on broken model
_bart_model        = None
_bart_tokenizer    = None
_bart_load_failed  = False
_embed_model       = None   # SentenceTransformer
_embed_load_failed = False


# ══════════════════════════════════════════════════════════════════════════════
# NLLB Translation Model
# ══════════════════════════════════════════════════════════════════════════════

def get_nllb():
    """Return (model, tokenizer) — lazy-loaded NLLB translation model.
    Raises RuntimeError immediately if model previously failed to load,
    preventing repeated reload attempts on corrupt/missing model files.
    """
    global _nllb_model, _nllb_tokenizer, _nllb_load_failed
    if _nllb_load_failed:
        raise RuntimeError("[NLLB] Model unavailable (load previously failed) — use API fallback.")
    if _nllb_model is None:
        print("[LOCAL_MODELS] Loading NLLB translation model from local disk...")
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            _nllb_tokenizer = AutoTokenizer.from_pretrained(
                NLLB_TOKENIZER_DIR, local_files_only=True, use_fast=True
            )
            _nllb_model = AutoModelForSeq2SeqLM.from_pretrained(
                NLLB_MODEL_DIR, local_files_only=True,
                dtype=torch.float16 if DEVICE.type == "cuda" else torch.float32,
            ).to(DEVICE)
            _nllb_model.eval()
            print(f"[LOCAL_MODELS] NLLB ready on {DEVICE}.")
        except Exception as load_err:
            _nllb_load_failed = True
            _nllb_model       = None
            _nllb_tokenizer   = None
            raise RuntimeError(f"[NLLB] Failed to load model: {load_err}") from load_err
    return _nllb_model, _nllb_tokenizer


def translate_with_nllb(
    text: str,
    src_lang: str = "auto",
    tgt_lang: str = "en",
    max_new_tokens: int = 512,
) -> str:
    """
    Translate text using the local NLLB model.

    Args:
        text:           Source text (Hindi, Marathi, etc.)
        src_lang:       ISO 639-1 code ('hi', 'mr', ...) or 'auto'
                        If 'auto', the caller must resolve this before calling.
        tgt_lang:       Target language ISO 639-1 code (default 'en')
        max_new_tokens: Max output tokens per chunk call.

    Returns:
        Translated text string.

    Raises:
        ValueError if language code is not in NLLB_LANG_MAP.
    """
    if src_lang == "auto" or src_lang not in NLLB_LANG_MAP:
        raise ValueError(
            f"[NLLB] Unknown src_lang '{src_lang}'. Resolve language before calling translate_with_nllb()."
        )
    if tgt_lang not in NLLB_LANG_MAP:
        raise ValueError(f"[NLLB] Unknown tgt_lang '{tgt_lang}'.")

    src_flores = NLLB_LANG_MAP[src_lang]
    tgt_flores = NLLB_LANG_MAP[tgt_lang]

    model, tokenizer = get_nllb()

    # Tokenize with source language set
    tokenizer.src_lang = src_flores
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
        padding=True,
    ).to(DEVICE)

    forced_bos = tokenizer.convert_tokens_to_ids(tgt_flores)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            forced_bos_token_id=forced_bos,
            max_new_tokens=max_new_tokens,
            num_beams=4,
            early_stopping=True,
        )

    return tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()


def translate_chunks_nllb(
    text: str,
    src_lang: str,
    tgt_lang: str = "en",
    chunk_chars: int = 800,
) -> str:
    """
    Split a large document into ~800-char chunks and translate each with NLLB.
    Returns the full translated text, OR an empty string if ALL chunks failed
    (so the caller can fall back to Gemini/Groq).
    """
    import re
    sentences = re.split(r'(?<=[।.!?\n])\s*', text)

    chunks, current = [], ""
    for sent in sentences:
        candidate = (current + " " + sent).strip() if current else sent
        if len(candidate) <= chunk_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sent[:chunk_chars]
    if current:
        chunks.append(current)

    parts, failed = [], 0
    for i, chunk in enumerate(chunks, 1):
        chunk = chunk.strip()
        if not chunk:
            continue
        print(f"[NLLB] Translating chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
        try:
            translated = translate_with_nllb(chunk, src_lang, tgt_lang)
            parts.append(translated)
        except Exception as e:
            print(f"[NLLB] Chunk {i} failed: {e}")
            failed += 1
            # Do NOT append original chunk — if we can't translate, return empty
            # so the caller falls back to a proper translation API

    if failed == len(chunks):
        # Every chunk failed (model broken) — signal full fallback
        print("[NLLB] All chunks failed. Falling back to API translation.")
        return ""

    return "\n\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# BART Summarization Model
# ══════════════════════════════════════════════════════════════════════════════

def get_bart():
    """Return (model, tokenizer) — lazy-loaded BART summarization model.
    Raises RuntimeError if model previously failed to load.
    """
    global _bart_model, _bart_tokenizer, _bart_load_failed
    if _bart_load_failed:
        raise RuntimeError("[BART] Model unavailable (load previously failed) — use Groq fallback.")
    if _bart_model is None:
        print("[LOCAL_MODELS] Loading BART summarization model from local disk...")
        try:
            from transformers import AutoTokenizer, BartForConditionalGeneration
            _bart_tokenizer = AutoTokenizer.from_pretrained(
                BART_TOKENIZER_DIR, local_files_only=True, use_fast=True
            )
            _bart_model = BartForConditionalGeneration.from_pretrained(
                BART_MODEL_DIR, local_files_only=True,
                dtype=torch.float32,
            ).to(DEVICE)
            _bart_model.eval()
            print(f"[LOCAL_MODELS] BART ready on {DEVICE}.")
        except Exception as load_err:
            _bart_load_failed  = True
            _bart_model        = None
            _bart_tokenizer    = None
            raise RuntimeError(f"[BART] Failed to load model: {load_err}") from load_err
    return _bart_model, _bart_tokenizer


def summarize_with_bart(
    text: str,
    max_input_chars: int = 3000,
    min_length: int = 56,
    max_length: int = 200,
    num_beams: int = 4,
) -> str:
    """
    Generate an extractive/abstractive summary of English legal text using
    the local BART model.

    Args:
        text:             English document text (will be truncated to max_input_chars).
        max_input_chars:  Chars to feed in (BART has 1024-token limit; ~3000 chars ≈ 700 tokens).
        min_length:       Minimum summary length in tokens.
        max_length:       Maximum summary length in tokens.
        num_beams:        Beam search width.

    Returns:
        Summary string.
    """
    model, tokenizer = get_bart()

    truncated = text[:max_input_chars]
    inputs = tokenizer(
        truncated,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    ).to(DEVICE)

    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            num_beams=num_beams,
            min_length=min_length,
            max_length=max_length,
            length_penalty=2.0,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )

    return tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()


# ══════════════════════════════════════════════════════════════════════════════
# MuRIL Multilingual Embedding Model (for RAG)
# ══════════════════════════════════════════════════════════════════════════════

def get_embedding_model():
    """Return a SentenceTransformer loaded from the local embedding_model/ folder.
    Raises RuntimeError if model previously failed to load.
    """
    global _embed_model, _embed_load_failed
    if _embed_load_failed:
        raise RuntimeError("[EMBED] Model unavailable (load previously failed) — use API fallback.")
    if _embed_model is None:
        print("[LOCAL_MODELS] Loading multilingual embedding model from local disk...")
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer(
                EMBED_MODEL_DIR,
                device=str(DEVICE),
                local_files_only=True,
            )
            print(f"[LOCAL_MODELS] Embedding model ready on {DEVICE}.")
        except Exception as load_err:
            _embed_load_failed = True
            _embed_model       = None
            raise RuntimeError(f"[EMBED] Failed to load model: {load_err}") from load_err
    return _embed_model


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Encode a list of texts (in any language supported by MuRIL) into
    normalized float vectors.

    Args:
        texts:      List of strings (Hindi, Marathi, English, or mixed).
        batch_size: GPU batch size.

    Returns:
        List of embedding vectors (list of floats).
    """
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=len(texts) > 50,
    )
    return embeddings.tolist()


# ══════════════════════════════════════════════════════════════════════════════
# Health check / CLI test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("LOCAL MODEL HEALTH CHECK")
    print("="*60)

    # 1. Translation test
    sample_hi = "आरोपी ने दिनांक 15/03/2025 को शिकायतकर्ता का मोबाईल चुराया।"
    print(f"\n[TEST] NLLB Translation")
    print(f"  Input (Hindi):  {sample_hi}")
    translated = translate_with_nllb(sample_hi, src_lang="hi", tgt_lang="en")
    print(f"  Output (English): {translated}")

    sample_mr = "फिर्यादी यांनी पोलीस ठाण्यात तक्रार नोंदवली."
    print(f"\n[TEST] NLLB Translation")
    print(f"  Input (Marathi): {sample_mr}")
    translated_mr = translate_with_nllb(sample_mr, src_lang="mr", tgt_lang="en")
    print(f"  Output (English): {translated_mr}")

    # 2. Summarization test
    sample_en = (
        "This rental agreement is entered into between the Landlord, Mr. Ramesh Sharma, "
        "and the Tenant, Ms. Priya Verma, for the property located at Flat 402, Mumbai. "
        "The monthly rent is Rs. 15,000 payable by the 5th of each month. "
        "A security deposit of Rs. 45,000 has been paid. "
        "The notice period for termination is 30 days. "
        "The tenant shall not sublet the premises without prior written consent."
    )
    print(f"\n[TEST] BART Summarization")
    summary = summarize_with_bart(sample_en)
    print(f"  Summary: {summary}")

    # 3. Embedding test
    print(f"\n[TEST] MuRIL Embeddings")
    texts = ["FIR filed at Andheri police station", "पोलीस ठाण्यात तक्रार नोंदवली", "जमानत अर्जी"]
    vecs = embed_texts(texts)
    print(f"  Embedded {len(vecs)} texts, vector dim = {len(vecs[0])}")

    print("\n✅ All local models working correctly.")
