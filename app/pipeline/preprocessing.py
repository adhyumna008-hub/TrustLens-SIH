import librosa
import numpy as np
import soundfile as sf

TARGET_SR = 16000


def preprocess_audio(input_path: str, output_path: str) -> dict:
    """
    Load audio, resample to 16kHz mono, trim leading/trailing silence,
    and write the cleaned WAV to output_path.

    Returns metadata used later to decide whether to flag the result
    as low-confidence due to poor input quality.
    """
    y, sr = librosa.load(input_path, sr=TARGET_SR, mono=True)

    if y.size == 0:
        raise ValueError("Empty or unreadable audio file")

    y_trimmed, _ = librosa.effects.trim(y, top_db=25)
    if y_trimmed.size == 0:
        # Entire clip fell below the silence threshold — keep the original
        # rather than writing an empty file.
        y_trimmed = y

    duration_sec = len(y_trimmed) / TARGET_SR
    rms = float(np.sqrt(np.mean(y_trimmed ** 2))) if y_trimmed.size else 0.0

    sf.write(output_path, y_trimmed, TARGET_SR)

    low_quality = duration_sec < 1.0 or rms < 0.005

    return {
        "duration_sec": duration_sec,
        "rms": rms,
        "sample_rate": TARGET_SR,
        "low_quality": low_quality,
    }
