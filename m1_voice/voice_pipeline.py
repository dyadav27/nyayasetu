"""
M1 — Voice Pipeline  [GPU-ACCELERATED — SpeechT5 on RTX 4050]
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

GPU usage:
  SpeechT5 TTS model + HiFiGAN vocoder → ~350 MB VRAM on RTX 4050
  ASR (Bhashini) is API-based — no local GPU needed for ASR.

Flow:
  WhatsApp OGG → Bhashini ASR → English text
  English text → Bhashini NMT → Regional text → SpeechT5 GPU → WAV bytes
"""

import os, sys, io, json, time, base64, requests, tempfile
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import torch
import scipy.io.wavfile as wav_io
from dotenv import load_dotenv
from pydantic import BaseModel
from gpu_utils import DEVICE, print_gpu_status, clear_gpu_cache

load_dotenv()

BHASHINI_API_KEY  = os.getenv("BHASHINI_API_KEY", "")
BHASHINI_USER_ID  = os.getenv("BHASHINI_USER_ID", "")
BHASHINI_BASE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model"
BHASHINI_INFER    = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")

LANG_CODES = {"marathi": "mr", "hindi": "hi", "english": "en"}


class TranscriptionResult(BaseModel):
    original_audio_lang: str
    transcribed_text:    str
    english_text:        str
    confidence:          float
    asr_engine_used:     str

class TTSResult(BaseModel):
    audio_bytes:   bytes
    audio_format:  str
    duration_secs: float
    language:      str
    tts_engine:    str


# ── Bhashini helpers ──────────────────────────────────────────────────────────
def _bhashini_headers():
    return {
        "userID":       BHASHINI_USER_ID,
        "ulcaApiKey":   BHASHINI_API_KEY,
        "Content-Type": "application/json",
    }

def _get_bhashini_pipeline(task: str, src: str, tgt: str = None) -> tuple[str, dict]:
    """Get service_id and inference headers for a Bhashini pipeline task."""
    lang_cfg = {"sourceLanguage": src}
    if tgt:
        lang_cfg["targetLanguage"] = tgt

    payload = {
        "pipelineTasks": [{"taskType": task, "config": {"language": lang_cfg}}],
        "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"},
    }
    resp = requests.post(
        f"{BHASHINI_BASE_URL}/getModelsPipeline",
        json=payload, headers=_bhashini_headers(), timeout=15
    )
    resp.raise_for_status()
    config = resp.json()

    service_id = ""
    for item in config.get("pipelineResponseConfig", []):
        if item.get("taskType") == task:
            service_id = item["config"][0].get("serviceId", "")
            break

    infer_key = (config.get("pipelineInferenceAPIEndPoint", {})
                       .get("inferenceApiKey", {})
                       .get("value", BHASHINI_API_KEY))
    return service_id, {"Authorization": infer_key, "Content-Type": "application/json"}


# ── Bhashini ASR ──────────────────────────────────────────────────────────────
def bhashini_asr(audio_bytes: bytes, lang: str = "mr") -> str:
    audio_b64  = base64.b64encode(audio_bytes).decode()
    service_id, infer_headers = _get_bhashini_pipeline("asr", lang)
    payload = {
        "pipelineTasks": [{"taskType": "asr", "config": {
            "serviceId": service_id,
            "language": {"sourceLanguage": lang},
            "audioFormat": "wav", "samplingRate": 16000,
        }}],
        "inputData": {"audio": [{"audioContent": audio_b64}]},
    }
    resp = requests.post(BHASHINI_INFER, json=payload,
                         headers=infer_headers, timeout=30)
    resp.raise_for_status()
    out = resp.json().get("pipelineResponse", [{}])[0].get("output", [{}])[0]
    return out.get("source", "")


# ── Whisper fallback ASR ──────────────────────────────────────────────────────
def whisper_asr(audio_bytes: bytes, lang: str = "mr") -> str:
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes); tmp = f.name
    try:
        with open(tmp, "rb") as f:
            return client.audio.transcriptions.create(
                model="whisper-1", file=f, language=lang
            ).text
    finally:
        os.unlink(tmp)


# ── Bhashini NMT ──────────────────────────────────────────────────────────────
def bhashini_translate(text: str, src: str, tgt: str) -> str:
    service_id, infer_headers = _get_bhashini_pipeline("translation", src, tgt)
    payload = {
        "pipelineTasks": [{"taskType": "translation", "config": {
            "serviceId": service_id,
            "language": {"sourceLanguage": src, "targetLanguage": tgt},
        }}],
        "inputData": {"input": [{"source": text}]},
    }
    resp = requests.post(BHASHINI_INFER, json=payload,
                         headers=infer_headers, timeout=30)
    resp.raise_for_status()
    out = resp.json().get("pipelineResponse", [{}])[0].get("output", [{}])[0]
    return out.get("target", text)


def google_translate_fallback(text: str, src: str, tgt: str) -> str:
    try:
        from googletrans import Translator
        return Translator().translate(text, src=src, dest=tgt).text
    except Exception:
        return text


# ── Bhashini TTS ──────────────────────────────────────────────────────────────
def bhashini_tts(text: str, lang: str = "mr") -> bytes:
    service_id, infer_headers = _get_bhashini_pipeline("tts", lang)
    payload = {
        "pipelineTasks": [{"taskType": "tts", "config": {
            "serviceId": service_id,
            "language": {"sourceLanguage": lang},
            "gender": "female", "samplingRate": 8000,
        }}],
        "inputData": {"input": [{"source": text}]},
    }
    resp = requests.post(BHASHINI_INFER, json=payload,
                         headers=infer_headers, timeout=30)
    resp.raise_for_status()
    audio_b64 = (resp.json()
                 .get("pipelineResponse", [{}])[0]
                 .get("audio", [{}])[0]
                 .get("audioContent", ""))
    return base64.b64decode(audio_b64)


# ── SpeechT5 TTS — GPU ────────────────────────────────────────────────────────
class SpeechT5GPU:
    """
    SpeechT5 TTS running on RTX 4050.
    VRAM usage: ~350 MB (model + vocoder + inference)
    Latency: ~0.8 sec for 50-word sentence on RTX 4050
    """
    _model     = None
    _processor = None
    _vocoder   = None
    _embed     = None

    @classmethod
    def _load(cls):
        if cls._model is not None:
            return
        from transformers import (
            SpeechT5Processor,
            SpeechT5ForTextToSpeech,
            SpeechT5HifiGan,
        )
        from datasets import load_dataset

        print(f"[TTS] Loading SpeechT5 on {DEVICE}...")
        cls._processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        cls._model     = SpeechT5ForTextToSpeech.from_pretrained(
            "microsoft/speecht5_tts"
        ).to(DEVICE)
        cls._vocoder   = SpeechT5HifiGan.from_pretrained(
            "microsoft/speecht5_hifigan"
        ).to(DEVICE)

        # Speaker embedding (neutral female voice)
        embed_ds   = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        cls._embed = torch.tensor(embed_ds[7306]["xvector"]).unsqueeze(0).to(DEVICE)

        # Half-precision for memory efficiency (RTX 4050 has FP16 tensor cores)
        cls._model   = cls._model.half()
        cls._vocoder = cls._vocoder.half()
        cls._embed   = cls._embed.half()

        print_gpu_status("SpeechT5 loaded")
        print("[TTS] ✅ SpeechT5 + HiFiGAN ready on GPU (FP16)")

    @classmethod
    def synthesise(cls, text: str) -> bytes:
        """Synthesise text → WAV bytes on GPU."""
        cls._load()

        # Truncate to 500 chars (SpeechT5 token limit)
        text = text[:500]
        inputs = cls._processor(text=text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(DEVICE)

        with torch.no_grad(), torch.cuda.amp.autocast():   # AMP for FP16
            speech = cls._model.generate_speech(
                input_ids,
                cls._embed,
                vocoder=cls._vocoder,
            )

        # speech is a 1D tensor on GPU — move to CPU for WAV writing
        speech_np = speech.cpu().float().numpy()

        buf = io.BytesIO()
        wav_io.write(buf, rate=16000, data=speech_np)
        return buf.getvalue()


# ── OGG ↔ WAV conversion (pydub + ffmpeg) ────────────────────────────────────
def ogg_to_wav(ogg_bytes: bytes) -> bytes:
    from pydub import AudioSegment
    audio = AudioSegment.from_ogg(io.BytesIO(ogg_bytes))
    audio = audio.set_frame_rate(16000).set_channels(1)
    out   = io.BytesIO()
    audio.export(out, format="wav")
    return out.getvalue()

def wav_to_ogg(wav_bytes: bytes) -> bytes:
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
    out   = io.BytesIO()
    audio.export(out, format="ogg", codec="libopus")
    return out.getvalue()


# ── Main VoicePipeline ────────────────────────────────────────────────────────
class VoicePipeline:

    def __init__(self, preferred_lang: str = "marathi"):
        self.lang = LANG_CODES.get(preferred_lang, "mr")

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        t0         = time.time()
        engine     = "bhashini"
        regional   = ""

        # ASR: Bhashini → Whisper fallback
        try:
            regional = bhashini_asr(audio_bytes, self.lang)
            if not regional.strip():
                raise ValueError("Empty ASR result")
        except Exception as e:
            print(f"[ASR] Bhashini failed ({e}), trying Whisper...")
            try:
                regional = whisper_asr(audio_bytes, self.lang)
                engine   = "whisper"
            except Exception as e2:
                print(f"[ASR] Whisper also failed: {e2}")
                regional = ""

        # Translate to English
        english = regional
        if self.lang != "en" and regional:
            try:
                english = bhashini_translate(regional, self.lang, "en")
            except Exception as e:
                print(f"[NMT] Bhashini failed ({e}), trying Google...")
                english = google_translate_fallback(regional, self.lang, "en")

        print(f"[ASR] Done in {time.time()-t0:.2f}s | {engine}")
        print(f"[ASR] Regional: {regional[:80]}")
        print(f"[ASR] English:  {english[:80]}")

        return TranscriptionResult(
            original_audio_lang=self.lang,
            transcribed_text=regional,
            english_text=english,
            confidence=-1.0,
            asr_engine_used=engine,
        )

    def synthesise_reply(self, english_text: str) -> TTSResult:
        t0     = time.time()
        engine = "speecht5_gpu"

        # Translate English → regional
        regional = english_text
        if self.lang != "en":
            try:
                regional = bhashini_translate(english_text, "en", self.lang)
            except Exception as e:
                print(f"[TTS-NMT] Bhashini failed ({e}), using Google...")
                regional = google_translate_fallback(english_text, "en", self.lang)

        # TTS: Bhashini (regional voice) → SpeechT5 GPU (English fallback)
        audio_bytes = b""
        try:
            audio_bytes = bhashini_tts(regional, self.lang)
            engine      = "bhashini_tts"
            print(f"[TTS] Bhashini TTS done: {len(audio_bytes):,} bytes")
        except Exception as e:
            print(f"[TTS] Bhashini failed ({e}), using SpeechT5 GPU...")
            # SpeechT5 is English — pass English text as fallback
            audio_bytes = SpeechT5GPU.synthesise(english_text)
            engine      = "speecht5_gpu"

        duration = len(audio_bytes) / (16000 * 2)   # rough: 16kHz, 16-bit
        print(f"[TTS] Done in {time.time()-t0:.2f}s | {engine} | {len(audio_bytes):,} bytes")
        print_gpu_status("after TTS")

        return TTSResult(
            audio_bytes=audio_bytes,
            audio_format="wav",
            duration_secs=duration,
            language=self.lang,
            tts_engine=engine,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────
_pipelines: dict = {}
def get_voice_pipeline(language: str = "marathi") -> VoicePipeline:
    if language not in _pipelines:
        _pipelines[language] = VoicePipeline(language)
    return _pipelines[language]


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys

    # Test TTS on GPU first (no audio file needed)
    print("\n[TEST] SpeechT5 GPU synthesis test...")
    audio = SpeechT5GPU.synthesise(
        "Your complaint has been registered. The applicable section is BNS Section 303 for theft."
    )
    with open("test_tts_output.wav", "wb") as f:
        f.write(audio)
    print(f"[TEST] TTS output saved: test_tts_output.wav ({len(audio):,} bytes)")
    print_gpu_status("after TTS test")

    # Test transcription if OGG file provided
    if len(_sys.argv) > 1:
        path = _sys.argv[1]
        with open(path, "rb") as f:
            raw = f.read()
        if path.endswith(".ogg"):
            raw = ogg_to_wav(raw)
        pipeline = get_voice_pipeline("marathi")
        result   = pipeline.transcribe(raw)
        print(f"\nTranscription result:")
        print(f"  Regional: {result.transcribed_text}")
        print(f"  English:  {result.english_text}")
        print(f"  Engine:   {result.asr_engine_used}")
