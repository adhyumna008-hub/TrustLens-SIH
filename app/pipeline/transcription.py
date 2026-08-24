import logging
from typing import Optional

logger = logging.getLogger("trustlens.transcription")

_whisper_model = None
_load_attempted = False


def _load_model():
    global _whisper_model, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    try:
        from faster_whisper import WhisperModel

        from app.config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_SIZE

        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE
        )
        logger.info(f"Loaded faster-whisper model: {WHISPER_MODEL_SIZE}")
    except Exception as e:
        logger.warning(f"Could not load faster-whisper model: {e}")


def transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Returns transcript text, or None if transcription failed/unavailable.
    Callers should treat None as "skip conversation-risk stage" per the spec,
    not as an error.
    """
    _load_model()
    if _whisper_model is None:
        return None
    try:
        segments, _info = _whisper_model.transcribe(audio_path, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text if text else None
    except Exception as e:
        logger.warning(f"Transcription failed: {e}")
        return None
