import logging

import librosa
import numpy as np

from app.config import SPOOF_MODEL_NAME

logger = logging.getLogger("trustlens.voice_detection")

_model_pipeline = None
_model_load_attempted = False


def _try_load_model():
    """
    Lazily loads the HF anti-spoofing classifier on first use, once per process.
    If it fails for any reason (model missing, no internet, incompatible output
    labels, etc.) we log a warning and every future call falls back to the
    heuristic detector below.
    """
    global _model_pipeline, _model_load_attempted
    if _model_load_attempted:
        return
    _model_load_attempted = True
    try:
        from transformers import pipeline as hf_pipeline
        _model_pipeline = hf_pipeline("audio-classification", model=SPOOF_MODEL_NAME)
        logger.info(f"Loaded voice-detection model: {SPOOF_MODEL_NAME}")
    except Exception as e:
        logger.warning(
            f"Could not load anti-spoofing model '{SPOOF_MODEL_NAME}': {e}. "
            "Falling back to heuristic spectral-artifact detector for this run."
        )


def _heuristic_spoof_score(audio_path: str) -> tuple[float, float]:
    """
    Weak-signal fallback used only when the real classifier can't load.
    Estimates 'syntheticness' from pitch jitter (real voices wobble more)
    and spectral flatness (synthetic voices are often smoother/flatter).
    This is NOT a trained detector — treat its output as experimental only.

    Returns (synthetic_probability, confidence).
    """
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    if y.size < sr * 0.5:
        return 0.5, 0.2  # too short to say anything meaningful

    f0, _, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
    )
    voiced_f0 = f0[~np.isnan(f0)] if f0 is not None else np.array([])

    if voiced_f0.size > 5:
        jitter = float(np.mean(np.abs(np.diff(voiced_f0))) / (np.mean(voiced_f0) + 1e-6))
    else:
        jitter = 0.0

    spectral_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    # Low natural jitter and/or unusually high flatness nudge the score toward "synthetic".
    jitter_signal = np.clip(1.0 - (jitter / 0.05), 0.0, 1.0)
    flatness_signal = np.clip((spectral_flatness - 0.15) / 0.35, 0.0, 1.0)

    synthetic_prob = float(np.clip(0.5 * jitter_signal + 0.5 * flatness_signal, 0.02, 0.98))
    confidence = 0.35  # heuristic method — deliberately capped, never reported as high-confidence

    return synthetic_prob, confidence


def detect_synthetic_voice(audio_path: str) -> dict:
    """
    Returns:
        {
            "synthetic_probability": float 0-1,
            "confidence": float 0-1,
            "mode": "model" | "experimental",
        }
    """
    _try_load_model()

    if _model_pipeline is not None:
        try:
            results = _model_pipeline(audio_path)  # list of {"label": ..., "score": ...}

            synthetic_prob = 0.0
            matched_spoof_label = False
            for r in results:
                label = r.get("label", "").lower()
                if any(k in label for k in ("spoof", "fake", "synthetic", "clone")):
                    synthetic_prob = max(synthetic_prob, float(r["score"]))
                    matched_spoof_label = True

            if not matched_spoof_label and results:
                top = max(results, key=lambda r: r["score"])
                if any(k in top["label"].lower() for k in ("bonafide", "real", "human")):
                    synthetic_prob = 1.0 - float(top["score"])
                else:
                    synthetic_prob = float(top["score"])

            confidence = float(max((r["score"] for r in results), default=0.5))
            return {
                "synthetic_probability": round(synthetic_prob, 4),
                "confidence": round(confidence, 4),
                "mode": "model",
            }
        except Exception as e:
            logger.warning(f"Model inference failed for this file, falling back to heuristic: {e}")

    synthetic_prob, confidence = _heuristic_spoof_score(audio_path)
    return {
        "synthetic_probability": round(synthetic_prob, 4),
        "confidence": round(confidence, 4),
        "mode": "experimental",
    }
