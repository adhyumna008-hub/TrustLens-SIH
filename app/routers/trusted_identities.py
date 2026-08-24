import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.config import VOICE_REF_DIR
from app.database import get_db
from app.models import TrustedIdentityRecord
from app.schemas import TrustedIdentityResponse

router = APIRouter(prefix="/trusted-identities", tags=["trusted-identities"])


@router.post("", response_model=TrustedIdentityResponse)
async def enroll_trusted_identity(
    contactName: str = Form(...),
    voiceSample: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Multipart keys here ("contactName", "voiceSample") match Android's Retrofit
    client exactly — not "contact_name"/"file" like the original draft assumed.
    """
    ext = Path(voiceSample.filename or "").suffix.lower() or ".wav"
    record = TrustedIdentityRecord(contact_name=contactName, embedding_ref="")
    db.add(record)
    db.commit()
    db.refresh(record)

    dest_path = VOICE_REF_DIR / f"{record.id}{ext}"
    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(voiceSample.file, out_file)

    # NOTE: stand-in embeddingRef (raw reference audio path) until real speaker
    # embeddings (e.g. pyannote.audio) are added — see README "Next steps".
    record.embedding_ref = str(dest_path)
    db.commit()

    return TrustedIdentityResponse(
        id=record.id, contactName=record.contact_name, embeddingRef=record.embedding_ref
    )


@router.get("", response_model=list[TrustedIdentityResponse])
def list_trusted_identities(db: Session = Depends(get_db)):
    records = db.query(TrustedIdentityRecord).all()
    return [
        TrustedIdentityResponse(id=r.id, contactName=r.contact_name, embeddingRef=r.embedding_ref)
        for r in records
    ]
