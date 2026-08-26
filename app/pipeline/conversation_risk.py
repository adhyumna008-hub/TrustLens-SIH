import logging

from app.pipeline.local_scam_detector import score_transcript

logger = logging.getLogger("trustlens.conversation_risk")


def analyze_conversation_risk(transcript: str) -> list[dict]:
    """
    Returns a list of dicts: [{"flagType": str, "excerpt": str, "confidence": float}, ...]
    Uses offline keyword-based scam detection - no API calls required.
    Returns [] if the transcript is too short or no scam patterns detected.
    """
    if not transcript or len(transcript.strip()) < 15:
        return []

    try:
        risk_score, matched_categories, evidence = score_transcript(transcript)

        # Convert matched categories to flag format
        flags = []
        for category, phrases in matched_categories.items():
            for phrase in phrases:
                # Use a reasonable confidence based on category weight
                confidence = min(0.9, 0.5 + (risk_score / 10.0))
                flags.append({
                    "flagType": category,
                    "excerpt": phrase,
                    "confidence": confidence,
                })

        logger.info(f"Local scam detection: score={risk_score:.2f}, categories={list(matched_categories.keys())}")
        return flags

    except Exception as e:
        logger.warning(f"Conversation-risk analysis failed: {e}")
        return []
