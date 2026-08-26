import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class CaseRecord(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=gen_id)
    created_at = Column(DateTime, default=datetime.utcnow)
    source_type = Column(String, default="IMPORT")

    # PENDING -> PREPROCESSING -> DETECTING_VOICE -> ANALYZING_CONVERSATION
    #         -> CALCULATING_RISK -> DONE  (or FAILED at any stage)
    status = Column(String, default="PENDING")

    risk_level = Column(String, nullable=True)          # LOW / MEDIUM / HIGH
    voice_score = Column(Float, nullable=True)           # synthetic-voice probability 0-1
    voice_confidence = Column(Float, nullable=True)
    voice_detection_mode = Column(String, nullable=True)  # "model" or "experimental"
    similarity_score = Column(Float, nullable=True)       # vs. enrolled trusted contact, if any

    # Individual risk components
    voice_risk = Column(Float, nullable=True)            # voice synthetic probability (0-1)
    conversation_risk = Column(Float, nullable=True)     # conversation scam probability (0-1)
    total_risk = Column(Float, nullable=True)            # combined scam probability (0-1)

    transcript = Column(Text, nullable=True)
    evidence_summary = Column(Text, nullable=True)  # JSON-encoded list[str]
    error_message = Column(Text, nullable=True)

    audio_path = Column(String, nullable=True)

    flags = relationship("TranscriptFlagRecord", back_populates="case", cascade="all, delete-orphan")


class TranscriptFlagRecord(Base):
    __tablename__ = "transcript_flags"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"))
    flag_type = Column(String)
    excerpt = Column(Text)
    confidence = Column(Float)

    case = relationship("CaseRecord", back_populates="flags")


class TrustedIdentityRecord(Base):
    __tablename__ = "trusted_identities"

    id = Column(String, primary_key=True, default=gen_id)
    contact_name = Column(String)
    embedding_ref = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
