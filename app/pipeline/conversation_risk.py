import json
import logging

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger("trustlens.conversation_risk")

SYSTEM_PROMPT = """You are a scam-call risk classifier for a fraud-prevention app called TrustLens.
Given a call transcript, identify manipulation patterns commonly used in impersonation/voice-cloning scams.

Respond with ONLY valid JSON, no preamble, no markdown fences, matching exactly this shape:
{
  "flags": [
    {"flagType": "string, short label e.g. 'urgency_language'", "excerpt": "short quote from transcript", "confidence": 0.0-1.0}
  ]
}

Look specifically for:
- urgency_language: pressure to act immediately, "don't tell anyone", panic-inducing framing
- money_or_otp_request: requests to transfer money, share OTP/PIN, gift cards, crypto
- emotional_manipulation: fear, guilt, impersonating a relative/authority in distress
- no_independent_verification_offered: caller discourages hanging up and calling back, or resists identity checks
- identity_claim: caller asserts an identity ("it's your son", "this is your bank") without proof

If the transcript is too short or ambiguous to assess, return {"flags": []}.
Do not invent flags not supported by the text. Quote the actual transcript for each excerpt."""


def analyze_conversation_risk(transcript: str) -> list[dict]:
    """
    Returns a list of dicts: [{"flagType": str, "excerpt": str, "confidence": float}, ...]
    Returns [] if the transcript is too short, the API key is missing, or the
    API call fails for any reason — callers treat that as "not applicable",
    per the spec, not as a pipeline failure.
    """
    if not transcript or len(transcript.strip()) < 15:
        return []

    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set; skipping conversation-risk analysis.")
        return []

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Transcript:\n\n{transcript}"}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        # Defensive cleanup in case the model wraps output in a code fence anyway.
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        parsed = json.loads(raw_text)
        flags = parsed.get("flags", [])

        cleaned = []
        for f in flags:
            try:
                cleaned.append({
                    "flagType": str(f["flagType"]),
                    "excerpt": str(f["excerpt"])[:500],
                    "confidence": float(f["confidence"]),
                })
            except (KeyError, ValueError, TypeError):
                continue  # skip malformed entries rather than failing the whole stage
        return cleaned

    except Exception as e:
        logger.warning(f"Conversation-risk analysis failed: {e}")
        return []
