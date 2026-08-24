from typing import Optional

HIGH_RISK_FLAG_TYPES = {"money_or_otp_request", "no_independent_verification_offered"}


def compute_risk(
    voice_synthetic_prob: float,
    voice_mode: str,
    conversation_flags: list[dict],
    similarity_score: Optional[float] = None,
) -> dict:
    """
    Deliberately simple and explainable — a judge (or user) should be able to
    read `evidence` and understand exactly why the score came out where it did.
    This is intentionally NOT another ML model.

    Returns: {"riskLevel": "LOW"|"MEDIUM"|"HIGH", "evidence": [str, ...], "score": float}
    """
    evidence: list[str] = []
    score = 0.0

    # --- Voice signal ---
    # Trust the heuristic fallback less than a real trained classifier.
    voice_weight = 0.5 if voice_mode == "model" else 0.25
    score += voice_synthetic_prob * voice_weight

    if voice_synthetic_prob >= 0.7:
        tag = "" if voice_mode == "model" else " (experimental signal — treat with caution)"
        evidence.append(f"High synthetic-voice probability ({voice_synthetic_prob:.0%}){tag}")
    elif voice_synthetic_prob >= 0.4:
        evidence.append(f"Moderate synthetic-voice indicators ({voice_synthetic_prob:.0%})")

    # --- Conversation signals ---
    conv_score = 0.0
    for flag in conversation_flags:
        weight = 0.15 if flag["flagType"] in HIGH_RISK_FLAG_TYPES else 0.08
        conv_score += weight * flag["confidence"]
        evidence.append(f"Detected: {flag['flagType'].replace('_', ' ')} — \"{flag['excerpt']}\"")
    score += min(conv_score, 0.4)  # cap so conversation signal alone can't max the score

    # --- Similarity signal (only present if a trusted-contact comparison was run) ---
    if similarity_score is not None:
        if similarity_score < 0.4:
            score += 0.15
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

    score = min(score, 1.0)

    if score >= 0.6:
        risk_level = "HIGH"
    elif score >= 0.3:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {"riskLevel": risk_level, "evidence": evidence, "score": round(score, 4)}
