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
