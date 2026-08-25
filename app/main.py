import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT
from app.database import Base, engine
from app.routers import cases, trusted_identities

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrustLens Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(trusted_identities.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
def announce_startup():
    log = logging.getLogger("trustlens.main")
    log.info(f"TrustLens backend ready — local base URL: http://{HOST}:{PORT}")
    log.info(f"From a physical Android phone on the same Wi-Fi, use: http://<this-computer's-LAN-IP>:{PORT}")
    log.info(f"Interactive API docs: http://localhost:{PORT}/docs")

    # Warm up models now, not on the first case — avoids a case looking "stuck"
    log.info("Pre-loading voice detection and transcription models (may take a few minutes on first run)...")
    from app.pipeline.voice_detection import _try_load_model as _load_voice_model
    from app.pipeline.transcription import _load_model as _load_whisper_model
    _load_voice_model()
    _load_whisper_model()
    log.info("Model warm-up complete.")
