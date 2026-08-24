import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import AUDIO_DIR
from app.database import get_db
from app.models import CaseRecord
from app.pipeline.orchestrator import run_pipeline
from app.schemas import (
    CaseCreateResponse,
    CaseResultResponse,
    TranscriptFlagOut,
    to_android_risk,
    to_android_status,
)

router = APIRouter(prefix="/cases", tags=["cases"])

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac", ".webm", ".3gp", ".mp4"}


def _to_result_response(case: CaseRecord) -> CaseResultResponse:
    evidence = json.loads(case.evidence_summary) if case.evidence_summary else []
    flags = [
        TranscriptFlagOut(flagType=f.flag_type, excerpt=f.excerpt, confidence=f.confidence)
        for f in case.flags
    ]
    return CaseResultResponse(
        caseId=case.id,
        status=to_android_status(case.status),
        riskLevel=to_android_risk(case.risk_level),
        voiceScore=case.voice_score,
        voiceConfidence=case.voice_confidence,
        voiceDetectionMode=case.voice_detection_mode,
        similarityScore=case.similarity_score,
        transcript=case.transcript,
        transcriptFlags=flags,
        evidence=evidence,
        errorMessage=case.error_message,
    )


@router.post("", response_model=CaseCreateResponse)
async def create_case(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    caseId: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Android's Retrofit client sends the file under the multipart key "audio"
    (not "file"), and generates its own caseId client-side (for Room + nav
    before the network call even returns) which we must honor as the primary
    key rather than discarding it in favor of a server-generated UUID.
    """
    ext = Path(audio.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    if caseId:
        existing = db.query(CaseRecord).filter(CaseRecord.id == caseId).first()
        if existing is not None:
            raise HTTPException(409, f"Case {caseId} already exists")
        case = CaseRecord(id=caseId, status="PENDING", source_type="IMPORT")
    else:
        case = CaseRecord(status="PENDING", source_type="IMPORT")

    db.add(case)
    db.commit()
    db.refresh(case)

    dest_path = AUDIO_DIR / f"{case.id}{ext}"
    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(audio.file, out_file)

    case.audio_path = str(dest_path)
    db.commit()

    background_tasks.add_task(run_pipeline, case.id)

    return CaseCreateResponse(caseId=case.id, status=to_android_status(case.status))


@router.get("/{case_id}", response_model=CaseResultResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if case is None:
        raise HTTPException(404, "Case not found")
    return _to_result_response(case)


@router.get("", response_model=list[CaseResultResponse])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(CaseRecord).order_by(CaseRecord.created_at.desc()).all()
    return [_to_result_response(c) for c in cases]
