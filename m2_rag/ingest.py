"""
M2 — RAG Engine: Ingestion Pipeline  [GPU-ACCELERATED]
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

GPU usage: sentence-transformers embedding runs on RTX 4050
           Batch size tuned for 6 GB VRAM (batch=256 safe)

Run once: python m2_rag/ingest.py
"""

import os, sys, json, hashlib
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import fitz                        # PyMuPDF
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
from gpu_utils import DEVICE, print_gpu_status, clear_gpu_cache

# ── Config ────────────────────────────────────────────────────────────────────
PDF_DIR       = "data/statutes"
CHROMA_DIR    = "data/chromadb"
COLLECTION    = "nyayasetu_legal"
EMBED_MODEL = r"C:\Users\Nitin Sharma\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\8b3219a92973c328a8e22fadcfa821b5dc75636a"
CHUNK_SIZE    = 512
CHUNK_OVERLAP = 50

# RTX 4050 has 6 GB — batch 256 uses ~800 MB VRAM, safe headroom
EMBED_BATCH   = 256

STATUTE_META = {
    "BNS.pdf":  {"act": "Bharatiya Nyaya Sanhita 2023",             "short": "BNS"},
    "BNSS.pdf": {"act": "Bharatiya Nagarik Suraksha Sanhita 2023",  "short": "BNSS"},
    "BSA.pdf":  {"act": "Bharatiya Sakshya Adhiniyam 2023",         "short": "BSA"},
    "BMC.pdf":  {"act": "BMC Bye-Laws Mumbai",                       "short": "BMC"},
}


def extract_text(pdf_path):
    doc   = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def chunk_pages(pages, filename):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    meta   = STATUTE_META.get(filename, {"act": filename, "short": filename})
    chunks = []
    for page_data in pages:
        for j, split in enumerate(splitter.split_text(page_data["text"])):
            cid = hashlib.md5(
                f"{filename}_{page_data['page']}_{j}_{split[:30]}".encode()
            ).hexdigest()
            chunks.append({
                "id":   cid,
                "text": split,
                "metadata": {
                    "source": filename,
                    "act":    meta["act"],
                    "short":  meta["short"],
                    "page":   str(page_data["page"]),
                    "chunk":  str(j),
                }
            })
    return chunks


def ingest_all():
    # ── Load embedder on GPU ──────────────────────────────────────────────────
    print(f"\n[INGEST] Loading embedding model on {DEVICE}...")
    embedder = SentenceTransformer(EMBED_MODEL, device=str(DEVICE))
    print_gpu_status("after embedder load")

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client     = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    print(f"[INGEST] Collection ready. Existing docs: {collection.count()}")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"[WARN] No PDFs in {PDF_DIR}")
        return

    for filename in pdf_files:
        path = os.path.join(PDF_DIR, filename)
        print(f"\n[PROCESSING] {filename}")
        pages  = extract_text(path)
        chunks = chunk_pages(pages, filename)
        print(f"  Pages: {len(pages)} | Chunks: {len(chunks)}")

        # Skip already-indexed
        existing = set(collection.get(ids=[c["id"] for c in chunks])["ids"])
        new      = [c for c in chunks if c["id"] not in existing]
        print(f"  New chunks to embed: {len(new)}")
        if not new:
            print("  [SKIP] Already indexed.")
            continue

        # GPU batch embedding
        for i in tqdm(range(0, len(new), EMBED_BATCH), desc=f"  GPU embed {filename}"):
            batch      = new[i : i + EMBED_BATCH]
            texts      = [c["text"]     for c in batch]
            ids        = [c["id"]       for c in batch]
            metadatas  = [c["metadata"] for c in batch]

            # encode() on GPU — SentenceTransformer respects `device` set at init
            embeddings = embedder.encode(
                texts,
                batch_size=EMBED_BATCH,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,     # cosine sim = dot product after norm
            ).tolist()

            collection.upsert(
                ids=ids, embeddings=embeddings,
                documents=texts, metadatas=metadatas,
            )

        print_gpu_status(f"after {filename}")
        clear_gpu_cache()

    print(f"\n[DONE] Total docs in ChromaDB: {collection.count()}")
    with open(os.path.join(CHROMA_DIR, "manifest.json"), "w") as f:
        json.dump({"collection": COLLECTION, "total": collection.count(),
                   "files": pdf_files}, f, indent=2)


if __name__ == "__main__":
    ingest_all()
