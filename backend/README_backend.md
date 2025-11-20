J.A.R.V.I.S Backend (Prototype)
================================

This is a minimal FastAPI backend scaffold for the J.A.R.V.I.S project.

Run locally (after installing requirements):

```bash
pip install -r requirements.txt
python -m uvicorn backend.app:app --reload
```

Endpoints:
- `GET /health` — simple health check
- `POST /projects` — create a new project (JSON: `{"title": "...", "description": "..."}`)
- `GET /projects` — list projects
- `GET /projects/{id}` — get project by id
- `POST /commands` — store a voice/command text payload

Data is stored in `data/jarvis.db` (SQLite) by default.
