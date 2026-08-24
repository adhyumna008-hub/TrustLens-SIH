import json
import logging
import os

from sqlalchemy.orm import Session

from app.config import AUDIO_DIR, DELETE_AUDIO_AFTER_PROCESSING
from app.database import SessionLocal
from app.models import CaseRecord, TranscriptFlagRecord
from app.pipeline.conversation_risk import analyze_conversation_risk
from app.pipeline.preprocessing import preprocess_audio
from app.pipeline.risk_engine import compute_risk
from app.pipeline.transcription import transcribe_audio
from app.pipeline.voice_detection import detect_synthetic_voice

logger = logging.getLogger("trustlens.orchestrator")


def run_pipeline(case_id: str):
    """
    Runs as a FastAPI BackgroundTask. Each stage updates CaseRecord.status so
    GET /cases/{id} can be polled for live progress from the Android app.
    """
    db: Session = SessionLocal()
    raw_path = None
    clean_path = None
    try:
        case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
        if case is None:
            logger.error(f"Case {case_id} not found for pipeline run")
            return

        raw_path = case.audio_path
        clean_path = str(AUDIO_DIR / f"{case_id}_clean.wav")

        # 1. Preprocessing
        case.status = "PREPROCESSING"
        db.commit()
        try:
            meta = preprocess_audio(raw_path, clean_path)
        except Exception as e:
            case.status = "FAILED"
            case.error_message = f"Preprocessing failed: {e}"
            db.commit()
            return

        if meta["low_quality"]:
            logger.info(f"Case {case_id}: low-quality audio flagged — proceeding with caution.")

        # 2. Voice detection
        case.status = "DETECTING_VOICE"
        db.commit()
        voice_result = detect_synthetic_voice(clean_path)
        case.voice_score = voice_result["synthetic_probability"]
        case.voice_confidence = voice_result["confidence"]
        case.voice_detection_mode = voice_result["mode"]
        db.commit()

        # 3. Transcription
        case.status = "ANALYZING_CONVERSATION"
        db.commit()
        transcript = transcribe_audio(clean_path)
        case.transcript = transcript
        db.commit()

        # 4. Conversation risk (skipped gracefully if no transcript — see spec)
        conversation_flags = []
        if transcript:
            conversation_flags = analyze_conversation_risk(transcript)
            for flag in conversation_flags:
                db.add(TranscriptFlagRecord(
                    case_id=case.id,
                    flag_type=flag["flagType"],
                    excerpt=flag["excerpt"],
                    confidence=flag["confidence"],
                ))
            db.commit()

        # 5. Risk engine
        case.status = "CALCULATING_RISK"
        db.commit()
        risk_result = compute_risk(
            voice_synthetic_prob=case.voice_score,
            voice_mode=case.voice_detection_mode,
            conversation_flags=conversation_flags,
            similarity_score=case.similarity_score,
        )
        case.risk_level = risk_result["riskLevel"]
        case.evidence_summary = json.dumps(risk_result["evidence"])
        case.status = "DONE"
        db.commit()

    except Exception as e:
        logger.exception(f"Pipeline failed for case {case_id}")
        try:
            case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
            if case:
                case.status = "FAILED"
                case.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        if DELETE_AUDIO_AFTER_PROCESSING:
            for p in (raw_path, clean_path):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
        db.close()
