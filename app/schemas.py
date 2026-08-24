from typing import List, Optional

from pydantic import BaseModel

# --- Android client contract ---
# The Android app's CaseStatus enum only knows PENDING / ANALYZING / DONE / FAILED,
# and its RiskLevel enum uses "MED" not "MEDIUM". The backend's internal pipeline
# stages are richer (useful for logs/debugging) but must be collapsed to these
# exact values before going out over the wire, or the app crashes on deserialization.

INTERNAL_TO_ANDROID_STATUS = {
    "PENDING": "PENDING",
    "PREPROCESSING": "ANALYZING",
    "DETECTING_VOICE": "ANALYZING",
    "ANALYZING_CONVERSATION": "ANALYZING",
    "CALCULATING_RISK": "ANALYZING",
    "DONE": "DONE",
    "FAILED": "FAILED",
}

INTERNAL_TO_ANDROID_RISK = {
    "LOW": "LOW",
    "MEDIUM": "MED",
    "HIGH": "HIGH",
}


def to_android_status(internal_status: str) -> str:
    return INTERNAL_TO_ANDROID_STATUS.get(internal_status, "ANALYZING")


def to_android_risk(internal_risk: Optional[str]) -> Optional[str]:
    if internal_risk is None:
        return None
    return INTERNAL_TO_ANDROID_RISK.get(internal_risk, internal_risk)


class TranscriptFlagOut(BaseModel):
    flagType: str
    excerpt: str
    confidence: float

    class Config:
        from_attributes = True


class CaseCreateResponse(BaseModel):
    caseId: str
    status: str


class CaseResultResponse(BaseModel):
    caseId: str
    status: str
    riskLevel: Optional[str] = None
    voiceScore: Optional[float] = None
    voiceConfidence: Optional[float] = None
    voiceDetectionMode: Optional[str] = None
    similarityScore: Optional[float] = None
    transcript: Optional[str] = None
    transcriptFlags: List[TranscriptFlagOut] = []
    evidence: List[str] = []
    errorMessage: Optional[str] = None


class TrustedIdentityResponse(BaseModel):
    id: str
    contactName: str
    embeddingRef: str
