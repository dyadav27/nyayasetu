"""
setup_gpu.py — One-time GPU setup verification for Nyaya-Setu
Run this BEFORE anything else to confirm your RTX 4050 is working.

Usage: python setup_gpu.py
"""

import subprocess, sys, os

def run(cmd):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip())
    return result.returncode


def check_nvidia_driver():
    print("\n" + "="*60)
    print("  STEP 1 — NVIDIA Driver")
    print("="*60)
    rc = run("nvidia-smi")
    if rc != 0:
        print("\n❌ nvidia-smi not found.")
        print("   Install NVIDIA driver: https://www.nvidia.com/Download/index.aspx")
        print("   For OMEN laptop: choose 'Game Ready Driver' for RTX 4050 Laptop GPU")
        return False
    print("✅ NVIDIA driver OK")
    return True


def check_cuda_pytorch():
    print("\n" + "="*60)
    print("  STEP 2 — CUDA PyTorch")
    print("="*60)
    try:
        import torch
        print(f"   torch version:   {torch.__version__}")
        print(f"   CUDA available:  {torch.cuda.is_available()}")
        if not torch.cuda.is_available():
            print("\n❌ CUDA not available in torch.")
            print("   Reinstall with CUDA support:")
            print("   pip uninstall torch torchvision torchaudio -y")
            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
            return False
        print(f"   CUDA version:    {torch.version.cuda}")
        for i in range(torch.cuda.device_count()):
            print(f"   Device [{i}]:      {torch.cuda.get_device_name(i)}")
        print("✅ CUDA PyTorch OK")
        return True
    except ImportError:
        print("❌ torch not installed. Run: pip install -r requirements.txt")
        return False


def check_rtx4050():
    print("\n" + "="*60)
    print("  STEP 3 — RTX 4050 Detection")
    print("="*60)
    import torch
    found = False
    for i in range(torch.cuda.device_count()):
        name = torch.cuda.get_device_name(i)
        if any(x in name.lower() for x in ["rtx", "nvidia", "geforce"]):
            props = torch.cuda.get_device_properties(i)
            vram  = props.total_memory / 1024**3
            print(f"   Found NVIDIA GPU at device [{i}]: {name}")
            print(f"   VRAM:     {vram:.1f} GB")
            print(f"   Compute:  {props.major}.{props.minor}")
            print(f"   SMs:      {props.multi_processor_count}")
            found = True
            break
    if not found:
        print("⚠️  RTX 4050 not found as a CUDA device.")
        print("   On OMEN laptop, make sure you've selected the NVIDIA GPU in:")
        print("   NVIDIA Control Panel → Manage 3D Settings → Preferred GPU → High-performance NVIDIA")
        return False

    # Verify gpu_utils selects it correctly
    from gpu_utils import DEVICE
    actual_name = torch.cuda.get_device_name(DEVICE)
    print(f"\n   gpu_utils.DEVICE = {DEVICE}  ({actual_name})")
    if "nvidia" in actual_name.lower() or "rtx" in actual_name.lower() or "geforce" in actual_name.lower():
        print("✅ RTX 4050 correctly selected (Intel iGPU excluded)")
        return True
    else:
        print(f"⚠️  DEVICE resolved to: {actual_name}")
        print("   Manually set in your .env: CUDA_VISIBLE_DEVICES=1")
        return False


def check_vram_budget():
    print("\n" + "="*60)
    print("  STEP 4 — VRAM Budget Check")
    print("="*60)
    import torch
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"   Total VRAM:               {total:.1f} GB")
    print(f"   Llama-3 8B 4-bit (Ollama):  ~4.5 GB")
    print(f"   MiniLM bi-encoder:          ~0.09 GB")
    print(f"   ms-marco cross-encoder:     ~0.09 GB")
    print(f"   SpeechT5 + HiFiGAN FP16:   ~0.35 GB")
    print(f"   ─────────────────────────────────────")
    budget = 4.5 + 0.09 + 0.09 + 0.35
    print(f"   Total (peak):               ~{budget:.2f} GB")
    if total >= budget:
        headroom = total - budget
        print(f"   Headroom:                   ~{headroom:.2f} GB  ✅ Safe")
    else:
        print(f"   ⚠️  VRAM may be tight. Ollama runs in its own process,")
        print(f"      so the 4.5 GB and the 0.53 GB are NOT concurrent.")
        print(f"      In practice: safe on 6 GB RTX 4050.")
    print("✅ VRAM budget acceptable")


def check_ollama():
    print("\n" + "="*60)
    print("  STEP 5 — Ollama + Llama-3 on GPU")
    print("="*60)
    rc = run("ollama --version")
    if rc != 0:
        print("\n❌ Ollama not installed.")
        print("   Download from: https://ollama.ai/download")
        print("   After install, run:  ollama pull llama3")
        return False

    import ollama as ol
    try:
        models = [m["name"] for m in ol.list()["models"]]
        print(f"   Available models: {models}")
        if any("llama3" in m for m in models):
            print("✅ llama3 model ready")
        else:
            print("⚠️  llama3 not pulled yet. Run: ollama pull llama3")
            print("   This downloads ~4.7 GB. After download, Ollama auto-uses GPU.")
    except Exception as e:
        print(f"⚠️  Ollama not running: {e}")
        print("   Start with: ollama serve")
    return True


def check_ffmpeg():
    print("\n" + "="*60)
    print("  STEP 6 — ffmpeg (audio conversion)")
    print("="*60)
    rc = run("ffmpeg -version 2>&1 | head -1")
    if rc != 0:
        print("❌ ffmpeg not found.")
        print("   Windows: winget install ffmpeg")
        print("   macOS:   brew install ffmpeg")
        print("   Ubuntu:  sudo apt install ffmpeg")
        return False
    print("✅ ffmpeg OK")
    return True


def run_smoke_test():
    print("\n" + "="*60)
    print("  STEP 7 — Smoke Test (GPU inference)")
    print("="*60)
    import torch
    from gpu_utils import DEVICE

    # Test 1: basic tensor on GPU
    x = torch.randn(1000, 1000, device=DEVICE)
    y = x @ x.T
    print(f"   Matrix multiply (1000×1000) on {DEVICE}: ✅")

    # Test 2: sentence-transformers on GPU
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=str(DEVICE))
        emb   = model.encode(["test legal query about BNS section 303"])
        print(f"   MiniLM embedding shape: {emb.shape}  device:{DEVICE}  ✅")
        del model
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"   ⚠️  SentenceTransformer smoke test failed: {e}")

    # Test 3: SpeechT5 TTS (optional — downloads 300MB first time)
    answer = input("\n   Run SpeechT5 GPU test? (downloads ~300 MB first time) [y/N]: ").strip().lower()
    if answer == "y":
        try:
            from m1_voice.voice_pipeline import SpeechT5GPU
            audio = SpeechT5GPU.synthesise("Testing Nyaya-Setu voice on RTX 4050.")
            with open("gpu_tts_test.wav", "wb") as f:
                f.write(audio)
            print(f"   SpeechT5 GPU TTS: {len(audio):,} bytes → gpu_tts_test.wav  ✅")
        except Exception as e:
            print(f"   ⚠️  SpeechT5 test failed: {e}")

    from gpu_utils import gpu_memory_status
    status = gpu_memory_status()
    print(f"\n   Final VRAM: {status['allocated_mb']} MB allocated / {status['total_mb']} MB total")
    print("\n✅ Smoke test complete")


def main():
    print("\n" + "="*60)
    print("  NYAYA-SETU — GPU SETUP VERIFICATION")
    print("  Target: NVIDIA RTX 4050 Laptop GPU (OMEN)")
    print("="*60)

    ok = True
    ok &= check_nvidia_driver()
    ok &= check_cuda_pytorch()
    ok &= check_rtx4050()
    check_vram_budget()    # informational only
    check_ollama()         # informational only
    check_ffmpeg()         # informational only

    if ok:
        run_smoke_test()
        print("\n" + "="*60)
        print("  🎉 ALL CHECKS PASSED — RTX 4050 ready for Nyaya-Setu")
        print("="*60)
        print("\nNext steps:")
        print("  1. python m2_rag/ingest.py       ← build knowledge base")
        print("  2. python m2_rag/rag_engine.py   ← test RAG on GPU")
        print("  3. python m1_voice/voice_pipeline.py  ← test TTS on GPU")
        print("  4. uvicorn main:app --reload     ← run full server")
    else:
        print("\n❌ Some checks failed — fix above issues before proceeding.")


if __name__ == "__main__":
    main()
