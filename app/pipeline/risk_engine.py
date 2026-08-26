from typing import Optional

# Risk categories from local scam detector
HIGH_RISK_CATEGORIES = {"otp_credential", "payment_request", "remote_access"}
MEDIUM_RISK_CATEGORIES = {"impersonation", "emotional_manipulation", "isolation_secrecy"}
MINIMUM_SAFETY_PERCENTAGE = 0.15  # 15% minimum risk for safety


def compute_risk(
    voice_synthetic_prob: float,
    voice_mode: str,
    conversation_flags: list[dict],
    similarity_score: Optional[float] = None,
) -> dict:
    """
    OR-based risk calculation: either strong voice signal OR strong conversation signal
    can independently escalate risk. Voice score never suppresses conversation risk.

    Returns: {
        "riskLevel": "LOW"|"MEDIUM"|"HIGH",
        "evidence": [str, ...],
        "voiceRisk": float (0-1),
        "conversationRisk": float (0-1),
        "totalRisk": float (0-1),
        "score": float
    }
    """
    evidence: list[str] = []

    # Extract conversation categories from flags
    matched_categories = set()
    conversation_risk_score = 0.0
    for flag in conversation_flags:
        flag_type = flag["flagType"]
        matched_categories.add(flag_type)
        conversation_risk_score += flag["confidence"]

    # --- Voice signal (only escalates, never suppresses) ---
    voice_flags_high = voice_synthetic_prob >= 0.7
    voice_flags_medium = voice_synthetic_prob >= 0.4

    if voice_flags_high:
        tag = "" if voice_mode == "model" else " (experimental signal — treat with caution)"
        evidence.append(f"High synthetic-voice probability ({voice_synthetic_prob:.0%}){tag}")
    elif voice_flags_medium:
        evidence.append(f"Moderate synthetic-voice indicators ({voice_synthetic_prob:.0%})")

    # --- Conversation signals (can independently escalate risk) ---
    has_high_risk_keyword = any(cat in matched_categories for cat in HIGH_RISK_CATEGORIES)
    has_medium_risk_keyword = any(cat in matched_categories for cat in MEDIUM_RISK_CATEGORIES)
    has_multiple_categories = len(matched_categories) >= 2

    for flag in conversation_flags:
        readable_flag = flag["flagType"].replace("_", " ").title()
        evidence.append(f"Detected: {readable_flag} — \"{flag['excerpt']}\"")

    # --- Similarity signal (only present if a trusted-contact comparison was run) ---
    if similarity_score is not None:
        if similarity_score < 0.4:
            evidence.append(
                f"Low voice similarity to enrolled trusted contact ({similarity_score:.0%}) "
                "— supporting signal only, not proof of identity"
            )
        else:
            evidence.append(
                f"Voice similarity to enrolled contact: {similarity_score:.0%} "
                "— supporting signal only, not proof of identity"
            )

    if not evidence:
        evidence.append("No strong risk indicators found in available signals.")

    # --- Calculate individual risk scores ---
    voice_risk = voice_synthetic_prob

    # Calculate conversation risk (normalized to 0-1)
    if conversation_flags:
        conversation_risk = min(conversation_risk_score / 3.0, 1.0)  # Normalize to 0-1
    else:
        conversation_risk = 0.0

    # --- OR-based risk calculation for risk level ---
    # Any strong signal from either channel should escalate risk
    if has_high_risk_keyword or has_multiple_categories or voice_flags_high:
        risk_level = "HIGH"
    elif has_medium_risk_keyword or conversation_risk_score >= 2.0 or voice_flags_medium:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # --- Total risk calculation (always minimum safety percentage) ---
    # Combine voice and conversation risks with weighting
    combined_risk = max(voice_risk, conversation_risk) * 0.7 + min(voice_risk, conversation_risk) * 0.3

    # Ensure minimum safety percentage
    total_risk = max(combined_risk, MINIMUM_SAFETY_PERCENTAGE)
    total_risk = min(total_risk, 1.0)  # Cap at 100%

    # Calculate a simple score for display
    score = total_risk

    return {
        "riskLevel": risk_level,
        "evidence": evidence,
        "voiceRisk": round(voice_risk, 4),
        "conversationRisk": round(conversation_risk, 4),
        "totalRisk": round(total_risk, 4),
        "score": round(score, 4)
    }
