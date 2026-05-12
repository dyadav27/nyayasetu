#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_missing_weights.py
===========================
Downloads the missing model weight files for Nyaya-Setu's local HuggingFace models.

The configs/tokenizers are already saved in hf_models/, but the actual
weight files (model.safetensors) are missing for:
  - hf_models/nllb_model/       (facebook/nllb-200-distilled-600M)
  - hf_models/embedding_model/  (google/muril-base-cased)

Run once from the project root:
    python download_missing_weights.py

Requirements: huggingface_hub  (pip install huggingface_hub)
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows so progress bars and arrows print cleanly
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent
HF_MODELS    = PROJECT_ROOT / "hf_models"


def _download_weights(hf_repo_id: str, local_dir: Path, filenames: list):
    """Download specific weight files from HuggingFace Hub into local_dir."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[ERROR] huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    local_dir.mkdir(parents=True, exist_ok=True)
    for fname in filenames:
        dest = local_dir / fname
        if dest.exists():
            size_mb = dest.stat().st_size // (1024 * 1024)
            print(f"  [SKIP] {fname} already present ({size_mb} MB)")
            continue
        print(f"  [DOWNLOAD] {hf_repo_id} -> {fname} ...", flush=True)
        try:
            downloaded = hf_hub_download(
                repo_id=hf_repo_id,
                filename=fname,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
            )
            size_mb = Path(downloaded).stat().st_size // (1024 * 1024)
            print(f"  [OK] {fname} saved ({size_mb} MB)")
        except Exception as e:
            print(f"  [FAIL] Could not download {fname}: {e}")
            raise


def download_nllb_weights():
    """Download NLLB-200-distilled-600M weights (~2.4 GB) and sentencepiece vocab."""
    print()
    print("=" * 60)
    print("NLLB-200-distilled-600M  (facebook/nllb-200-distilled-600M)")
    print("=" * 60)
    nllb_model_dir = HF_MODELS / "nllb_model"
    nllb_tok_dir   = HF_MODELS / "nllb_tokenizer"
    # Download model weights
    _download_weights(
        hf_repo_id="facebook/nllb-200-distilled-600M",
        local_dir=nllb_model_dir,
        filenames=["pytorch_model.bin"],
    )
    # The NllbTokenizerFast needs sentencepiece.bpe.model in the tokenizer folder
    _download_weights(
        hf_repo_id="facebook/nllb-200-distilled-600M",
        local_dir=nllb_tok_dir,
        filenames=["sentencepiece.bpe.model"],
    )


def download_muril_weights():
    """Download MuRIL-base-cased weights (~900 MB)."""
    print()
    print("=" * 60)
    print("MuRIL-base-cased  (google/muril-base-cased)")
    print("=" * 60)
    embed_dir = HF_MODELS / "embedding_model"
    _download_weights(
        hf_repo_id="google/muril-base-cased",
        local_dir=embed_dir,
        filenames=["pytorch_model.bin"],
    )


def verify_all():
    """Quick sanity check that all weights are present."""
    print()
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    checks = [
        ("NLLB model weights",  HF_MODELS / "nllb_model"      / "pytorch_model.bin"),
        ("NLLB sentencepiece",  HF_MODELS / "nllb_tokenizer"  / "sentencepiece.bpe.model"),
        ("BART model weights",  HF_MODELS / "bart_model"       / "model.safetensors"),
        ("Embedding weights",   HF_MODELS / "embedding_model"  / "pytorch_model.bin"),
    ]
    all_ok = True
    for label, path in checks:
        if path.exists():
            mb = path.stat().st_size // (1024 * 1024)
            print(f"  [OK]      {label}: {path.name}  ({mb} MB)")
        else:
            print(f"  [MISSING] {label}: {path}")
            all_ok = False

    print()
    if all_ok:
        print("All model weights present! Run the backend normally.")
    else:
        print("WARNING: Some weights are still missing. See above.")
        print("The backend will fall back to Gemini/Groq for missing models.")
    return all_ok


if __name__ == "__main__":
    print("Nyaya-Setu -- Model Weight Downloader")
    print("Downloads weights used on Kaggle that are not stored locally.")

    nllb_ok = True
    muril_ok = True

    try:
        download_nllb_weights()
    except Exception as e:
        nllb_ok = False
        print(f"[ERROR] NLLB download failed: {e}")
        print("        The system will fall back to Gemini/Groq for translation.")

    try:
        download_muril_weights()
    except Exception as e:
        muril_ok = False
        print(f"[ERROR] MuRIL download failed: {e}")
        print("        The system will fall back to all-MiniLM-L6-v2 for RAG embeddings.")

    verify_all()
