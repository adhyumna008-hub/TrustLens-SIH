import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import tempfile
import os

TARGET_SR = 16000


def get_audio_reliability_label(audio_metadata: dict) -> str:
    """
    Returns a reliability tag for the voice-detection result based on
    signal characteristics that suggest the audio may be out-of-distribution
    for the model (heavy compression, re-encoding, or low quality).
    """
    if audio_metadata.get("low_quality"):
        return "low_reliability"
    if audio_metadata.get("was_transcoded"):
        return "reduced_reliability"
    if audio_metadata.get("rms", 1.0) < 0.01:  # very quiet signal
        return "reduced_reliability"
    return "normal"


def preprocess_audio(input_path: str, output_path: str) -> dict:
    """
    Load audio, resample to 16kHz mono, trim leading/trailing silence,
    and write the cleaned WAV to output_path.

    Returns metadata used later to decide whether to flag the result
    as low-confidence due to poor input quality.
    """
    import traceback
    try:
        # Use pydub+ffmpeg for formats that librosa struggles with (M4A, AAC, etc.)
        # Fall back to librosa for standard formats
        input_ext = os.path.splitext(input_path)[1].lower()
        was_transcoded = False

        if input_ext in ['.m4a', '.aac', '.mp4', '.3gp']:
            # Convert problematic formats to WAV using pydub+ffmpeg
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()

            try:
                audio = AudioSegment.from_file(input_path)
                audio.export(temp_wav_path, format='wav')
                y, sr = librosa.load(temp_wav_path, sr=TARGET_SR, mono=True)
                was_transcoded = True
            finally:
                if os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
        else:
            # Use librosa directly for standard formats
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
            "was_transcoded": was_transcoded,
        }
    except Exception as e:
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        raise ValueError(f"Failed to process audio file: {error_details}")
