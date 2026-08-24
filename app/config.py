import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AUDIO_DIR = STORAGE_DIR / "audio"
VOICE_REF_DIR = STORAGE_DIR / "voice_refs"
DB_PATH = BASE_DIR / "trustlens.db"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VOICE_REF_DIR.mkdir(parents=True, exist_ok=True)

# --- Anthropic (conversation-risk classifier) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

# --- Voice detection ---
# NOTE: verify this checkpoint still exists/works on huggingface.co before a demo.
# If it fails to load for any reason, the pipeline automatically falls back to the
# heuristic spectral-artifact detector and labels the result "experimental".
SPOOF_MODEL_NAME = os.environ.get("SPOOF_MODEL_NAME", "MelodyMachine/Deepfake-audio-detection-V2")

# --- Transcription (faster-whisper, fully local) ---
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

# --- Privacy ---
DELETE_AUDIO_AFTER_PROCESSING = os.environ.get("DELETE_AUDIO_AFTER_PROCESSING", "true").lower() == "true"

# --- Server ---
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
