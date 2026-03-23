"""
gpu_utils.py — Central GPU/CUDA device management for Nyaya-Setu
All modules import from here instead of calling torch.cuda directly.

RTX 4050 Laptop specs:
  - VRAM: 6 GB GDDR6
  - CUDA Compute: 8.9 (Ada Lovelace)
  - Tensor Cores: 4th gen
  - Best for: inference with 4-bit / 8-bit quantised models

VRAM budget breakdown:
  - Llama-3 8B (4-bit via Ollama): ~4.5 GB  → handled by Ollama separately
  - sentence-transformers MiniLM:  ~90 MB
  - cross-encoder MiniLM:          ~90 MB
  - SpeechT5 TTS + HiFiGAN:        ~350 MB
  - ChromaDB (CPU):                 RAM only
  Total GPU peak (without Llama-3): ~530 MB  ← well within 6 GB
  Llama-3 runs in its own Ollama process: ~4.5 GB
"""

import os
import torch

# ── Force CUDA — disable Intel integrated GPU ──────────────────────────────────
# On your OMEN laptop, device 0 = Intel iGPU, device 1 = RTX 4050
# Set CUDA_VISIBLE_DEVICES to expose only the RTX 4050

def _find_nvidia_device() -> int:
    """
    Scan available CUDA devices and return the index of the first NVIDIA GPU.
    On OMEN laptops: Intel iGPU is device 0, NVIDIA is device 1.
    """
    if not torch.cuda.is_available():
        return -1
    for i in range(torch.cuda.device_count()):
        name = torch.cuda.get_device_name(i).lower()
        if "nvidia" in name or "geforce" in name or "rtx" in name or "gtx" in name:
            return i
    return 0  # fallback to device 0 if can't distinguish


def setup_gpu() -> torch.device:
    """
    Configure and return the correct torch.device.
    - Finds the NVIDIA RTX 4050 (not the Intel iGPU)
    - Sets CUDA_VISIBLE_DEVICES so all subsequent torch calls use it
    - Enables TF32 for faster matmul on Ada Lovelace
    - Returns the torch.device to use everywhere
    """
    if not torch.cuda.is_available():
        print("[GPU] ⚠️  CUDA not available. Running on CPU.")
        print("[GPU]     Make sure you installed CUDA PyTorch:")
        print("[GPU]     pip install torch --index-url https://download.pytorch.org/whl/cu121")
        return torch.device("cpu")

    nvidia_idx = _find_nvidia_device()

    if nvidia_idx == -1:
        print("[GPU] ⚠️  No NVIDIA GPU found. Running on CPU.")
        return torch.device("cpu")

    # Lock CUDA to only see the NVIDIA GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = str(nvidia_idx)
    os.environ["CUDA_DEVICE_ORDER"]    = "PCI_BUS_ID"

    # After setting CUDA_VISIBLE_DEVICES, it becomes device 0
    device = torch.device("cuda:0")

    # Enable TF32 — faster on Ampere/Ada, negligible accuracy loss for inference
    torch.backends.cuda.matmul.allow_tf32  = True
    torch.backends.cudnn.allow_tf32        = True
    torch.backends.cudnn.benchmark         = True   # auto-tune convolutions

    # Print GPU info
    props = torch.cuda.get_device_properties(device)
    vram_gb = props.total_memory / 1024**3
    print(f"[GPU] ✅ Using: {props.name}")
    print(f"[GPU]    VRAM:        {vram_gb:.1f} GB")
    print(f"[GPU]    CUDA:        {props.major}.{props.minor}")
    print(f"[GPU]    Multiproc:   {props.multi_processor_count}")
    print(f"[GPU]    TF32:        enabled")
    print(f"[GPU]    cuDNN bench: enabled")

    return device


def clear_gpu_cache():
    """Free unused VRAM. Call between model loads if running tight on memory."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def gpu_memory_status() -> dict:
    """Return current VRAM usage as a dict."""
    if not torch.cuda.is_available():
        return {"available": False}
    allocated = torch.cuda.memory_allocated() / 1024**2
    reserved  = torch.cuda.memory_reserved()  / 1024**2
    total     = torch.cuda.get_device_properties(0).total_memory / 1024**2
    return {
        "device":    torch.cuda.get_device_name(0),
        "allocated_mb": round(allocated, 1),
        "reserved_mb":  round(reserved,  1),
        "total_mb":     round(total,     1),
        "free_mb":      round(total - reserved, 1),
    }


def print_gpu_status(label: str = ""):
    status = gpu_memory_status()
    if status.get("available") is False:
        return
    tag = f"[{label}] " if label else ""
    print(f"[GPU] {tag}VRAM — "
          f"Allocated: {status['allocated_mb']} MB | "
          f"Reserved: {status['reserved_mb']} MB | "
          f"Free: {status['free_mb']} MB")


# ── Singleton device (import this in all modules) ─────────────────────────────
DEVICE = setup_gpu()


# ── CLI check ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  NYAYA-SETU GPU DIAGNOSTICS")
    print("="*55)
    print(f"  torch version:   {torch.__version__}")
    print(f"  CUDA available:  {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  Device count:    {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  Device [{i}]:      {torch.cuda.get_device_name(i)}")
        print(f"  Active device:   {torch.cuda.get_device_name(DEVICE)}")
    print("="*55)
    print_gpu_status("startup")
