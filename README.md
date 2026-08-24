# TrustLens Backend

Real (not mocked) backend for TrustLens: synthetic-voice detection + conversation-based
scam-risk scoring. Matches the API contract the Android app's `FakeCaseRepository`/
Retrofit interface already expects, so swapping the app onto this backend later should
only require pointing `BASE_URL` at wherever this is running.

## What it does

`POST /cases` (multipart audio upload) kicks off a background pipeline:

1. **Preprocessing** — resample to 16kHz mono, trim silence (librosa)
2. **Voice detection** — synthetic-voice probability via a Hugging Face anti-spoofing
   model, with an automatic heuristic fallback (labeled `"experimental"`) if the model
   can't load
3. **Transcription** — local, offline speech-to-text via faster-whisper
4. **Conversation risk** — Claude reads the transcript and returns structured scam-pattern
   flags (urgency language, OTP/money requests, emotional manipulation, etc.)
5. **Risk engine** — a transparent, weighted rule-based scorer (not another model) combines
   everything into LOW / MEDIUM / HIGH with a plain-English evidence list

`GET /cases/{id}` returns live status while processing, then the full result.

`POST /trusted-identities` stores a reference voice sample for a contact (embedding
extraction is stubbed for now — see "Next steps" below).

## Setup

```bash
cd trustlens-backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`torch` and `transformers` are the two heaviest installs — this can take several minutes,
especially on a slow connection. That's normal.

Set your Anthropic API key (required for the conversation-risk stage — everything else
still works without it, that stage just gets skipped):

```bash
cp .env.example .env
# edit .env and paste your real key
export $(cat .env | xargs)      # or use a tool like python-dotenv / direnv
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup it logs the base URL and points you to `http://localhost:8000/docs` for
interactive Swagger docs you can test from immediately — no phone or frontend needed.

## Testing it end-to-end before touching Android

```bash
# 1. Upload a short audio file (wav/mp3/m4a/ogg/etc.)
curl -X POST http://localhost:8000/cases -F "file=@/path/to/test_call.mp3"
# → {"id": "...", "status": "PENDING"}

# 2. Poll for the result (processing takes a bit the first time while models load)
curl http://localhost:8000/cases/<id-from-above>
```

You should see `status` progress through `PREPROCESSING` → `DETECTING_VOICE` →
`ANALYZING_CONVERSATION` → `CALCULATING_RISK` → `DONE`, then `riskLevel`, `voiceScore`,
and `transcriptFlags` populated. Confirm this JSON shape actually matches what your
Android `CaseEntity`/`TranscriptFlagEntity` expect before wiring up the app.

## Connecting from a physical Android phone

`localhost` on your laptop is not reachable from a phone. Find your laptop's LAN IP
(shown in the startup log, or `ipconfig`/`ifconfig`) and use that instead, e.g.
`http://192.168.1.42:8000`, with phone and laptop on the same Wi-Fi network. If you
deploy this somewhere (Render, Railway, Fly.io, etc.) later, use that public URL instead.

## Known limitations / honest caveats

- **`SPOOF_MODEL_NAME`** in `app/config.py` is a placeholder checkpoint name. Model
  availability on Hugging Face can change — verify it loads (check the startup logs for
  a warning) before relying on it for a demo. If it fails to load, the pipeline
  automatically and silently falls back to the heuristic detector and labels results
  `"experimental"` so nothing crashes — but a real trained classifier will be far more
  accurate than the heuristic, so it's worth confirming this works ahead of time.
- **Voice similarity** (`similarityScore`) is not computed yet — `POST /trusted-identities`
  currently stores the raw reference audio path as a stand-in `embeddingRef`. Real speaker
  embeddings (e.g. via `pyannote.audio`) are a good next module once the core pipeline is
  solid, per the build order in the original blueprint.
- **SQLite** is fine for a hackathon demo; if you deploy multi-user/institutional features
  later, migrate to Postgres.
- No auth/JWT yet — every endpoint is open. Fine for local dev, not for anything public.

## Next steps (do NOT bundle these into the Android integration prompt)

- Add real speaker-embedding similarity for trusted contacts
- Add JWT auth once the mobile app has a login flow
- Swap SQLite → Postgres if deploying for multiple users
- Add `POST /cases/{id}/report` (PDF export) and the admin/audit-log endpoints once the
  core pipeline is demonstrably working end-to-end
