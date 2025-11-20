# Organism-Designer
A web-based application for designing and visualizing 3D organisms with a comprehensive trait and analysis system.

## Backend (J.A.R.V.I.S. prototype)

This repository includes a small FastAPI-based backend prototype under `backend/` that provides an offline-first admin UI, settings audit log, and session management for local use.

Environment variables used by the backend:

- `JARVIS_ADMIN_TOKEN`: (required) legacy/master admin token. Used to exchange for a short-lived session via `/api/admin/login` if configured.
- `JARVIS_SESSION_KEY`: (optional) HMAC key used to sign stateless JWT-like session tokens. If set, login may return a signed token in addition to a stateful session.
- `JARVIS_SECURE_COOKIES`: set to `1` to mark admin cookies as `Secure` (recommended in production when using HTTPS).
- `JARVIS_AUTOSAVE_INTERVAL`: seconds between autosave snapshot runs (default `60`).
- `JARVIS_SESSION_CLEANUP_INTERVAL`: seconds between expired-session cleanup runs (default `300`).
- `JARVIS_REVOKED_CLEANUP_INTERVAL`: seconds between revoked-token cleanup runs (default `3600`).
- `JARVIS_REVOKE_RETENTION_SECONDS`: how long to keep revoked token records before cleanup (default 30 days).

Quick commands:

```bash
# run tests (in the repo virtualenv)
python -m pytest -q

# run the backend (development)
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Security notes:

- The admin login now issues an HttpOnly session cookie; web UIs rely on this cookie by default. Avoid storing master tokens in localStorage or shared browsers.
- The backend keeps an append-only audit log under `data/jarvis_settings.log` and a local SQLite DB at `data/jarvis.db`.

VOSK (optional, offline STT)
---------------------------------
This prototype supports offline speech-to-text using VOSK. To enable it locally:

1. Install the Python package:

```bash
pip install vosk
```

2. Download a small (or medium) VOSK model and place it under `models/vosk-model-small` relative to the repository root.
	Example (small English model):

```bash
mkdir -p models
cd models
curl -LO https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-small
cd ..
```

3. Restart the backend. The `/api/voice/status` endpoint will report whether the model is present and whether `vosk` and `pyttsx3` packages are available.

Notes:
- VOSK models are downloaded separately because they can be large. Keep them under `models/` for local-only, offline use.
- If `pyttsx3` is not installed, TTS endpoints will return a clear error indicating how to install it.

VOSK model (optional for offline STT)

This backend includes a VOSK-based transcription helper in `jarvis/voice.py`. To enable on-device transcription:

1. Install the Python dependency: `pip install vosk`.
2. Download a VOSK small English model and place it at `models/vosk-model-small` relative to the repository root. For example:

```bash
mkdir -p models
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-small
```

3. Restart the backend. The endpoint `GET /api/voice/status` will report whether the model is present.

If you don't want to install VOSK, the `/tts` endpoint still works if `pyttsx3` is installed.
