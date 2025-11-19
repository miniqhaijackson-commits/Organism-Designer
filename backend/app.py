from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Body
from fastapi.responses import JSONResponse
import os
import time
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from backend import db
from backend import settings as settings_mod
from backend.schemas import ProjectCreate, ProjectOut, CommandCreate
from jarvis.security import EnterpriseSecurity
from jarvis import voice
from fastapi.responses import FileResponse


app = FastAPI(title="J.A.R.V.I.S Backend (Prototype)")

# serve a minimal static UI
app.mount("/ui", StaticFiles(directory="backend/static", html=True), name="ui")


@app.on_event("startup")
def startup_event():
    # Ensure database is initialized on startup
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


def _verify_admin(request: Request):
    token = request.headers.get('x-admin-token')
    env = os.environ.get('JARVIS_ADMIN_TOKEN')
    if not env:
        # no admin token configured; deny for safety
        return False, None
    if token != env:
        return False, None
    actor = request.headers.get('x-admin-actor', 'admin')
    return True, actor


@app.post("/projects", response_model=ProjectOut)
def create_project(p: ProjectCreate):
    project_id = db.create_project(p.title, p.description or "")
    proj = db.get_project(project_id)
    return proj


@app.get("/projects", response_model=list[ProjectOut])
def list_projects():
    return db.list_projects()


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int):
    proj = db.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.post("/commands")
def post_command(c: CommandCreate, request: Request):
    # Basic enterprise security check
    es = EnterpriseSecurity()
    ok, msg = es.validate_command_safety(c.command_text)
    if not ok:
        return JSONResponse(status_code=400, content={"error": msg})

    # If command looks like device-control, require pairing token header
    pairing_token = request.headers.get("x-pairing-token")
    if "control" in c.command_text.lower() or "device:" in c.command_text.lower():
        if not pairing_token or not db.verify_pairing(pairing_token):
            return JSONResponse(status_code=401, content={"error": "Pairing required for device control"})

    cmd_id = db.create_command(c.command_text)
    return {"id": cmd_id, "status": "stored", "note": msg}



@app.get("/api/settings")
def get_settings(request: Request):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail="admin token required")
    return settings_mod.load_settings()


@app.post("/api/settings")
def post_settings(request: Request, payload: dict = Body(...), reason: str | None = None):
    ok, actor = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail="admin token required")
    # payload should be a dict of settings
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="settings payload must be an object")
    res = settings_mod.save_settings_atomic(payload, actor=actor or 'admin', reason=reason)
    return {"saved": True, "changed": res.get('changed', 0)}


@app.get("/api/logs")
def get_logs(request: Request, limit: int = 200):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail="admin token required")
    return settings_mod.get_audit_logs(limit=limit)



@app.post("/projects/{project_id}/files")
def upload_project_file(project_id: int, file: UploadFile = File(...)):
    data = file.file.read()
    path = db.add_project_file(project_id, file.filename, data)
    return {"path": path, "filename": file.filename}


@app.get("/projects/{project_id}/files")
def get_project_files(project_id: int):
    return db.list_project_files(project_id)


@app.post("/pairings")
def create_pairing(device_name: str = Form(...)):
    token = db.create_pairing(device_name)
    return {"token": token}


@app.post("/projects/{project_id}/snapshot")
def create_snapshot(project_id: int):
    try:
        sid = db.create_snapshot(project_id)
        return {"snapshot_id": sid}
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.get("/projects/{project_id}/snapshots")
def list_project_snapshots(project_id: int):
    return db.list_snapshots(project_id)


@app.post("/snapshots/{snapshot_id}/restore")
def restore_snapshot(snapshot_id: int):
    ok = db.restore_snapshot(snapshot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"restored": True}


def _autosave_loop(interval: int = 60):
    import threading, time

    def loop():
        while True:
            try:
                projects = db.list_projects()
                for p in projects:
                    try:
                        db.create_snapshot(p['id'])
                    except Exception:
                        # snapshot failure shouldn't kill loop
                        pass
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


@app.on_event("startup")
def startup_event():
    # Ensure database is initialized on startup
    db.init_db()
    # start autosave loop (interval configurable via env var)
    import os
    try:
        interval = int(os.environ.get("JARVIS_AUTOSAVE_INTERVAL", "60"))
    except Exception:
        interval = 60
    _autosave_loop(interval=interval)


@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    # Accept a PCM16 WAV file (mono). Return the transcribed text.
    data = file.file.read()
    try:
        text = voice.transcribe_wav_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"text": text}


@app.post("/tts")
def synthesize_tts(text: str = Form(...)):
    out_dir = Path(__file__).resolve().parent.parent / 'data' / 'tts'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tts_{int(time.time())}.wav"
    try:
        path = voice.speak_text_to_file(text, str(out_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(path, media_type='audio/wav', filename=out_path.name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, log_level="info")
