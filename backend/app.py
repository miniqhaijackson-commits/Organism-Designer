from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Body, Depends
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize DB and background loops
    db.init_db()
    try:
        interval = int(os.environ.get("JARVIS_AUTOSAVE_INTERVAL", "60"))
    except Exception:
        interval = 60
    _autosave_loop(interval=interval)
    try:
        cleanup_interval = int(os.environ.get('JARVIS_SESSION_CLEANUP_INTERVAL', '300'))
    except Exception:
        cleanup_interval = 300
    _session_cleanup_loop(interval=cleanup_interval)
    try:
        revoked_interval = int(os.environ.get('JARVIS_REVOKED_CLEANUP_INTERVAL', '3600'))
    except Exception:
        revoked_interval = 3600
    try:
        retention = int(os.environ.get('JARVIS_REVOKE_RETENTION_SECONDS', str(60 * 60 * 24 * 30)))
    except Exception:
        retention = 60 * 60 * 24 * 30
    _revoked_cleanup_loop(interval=revoked_interval, retention=retention)
    yield


app = FastAPI(title="J.A.R.V.I.S Backend (Prototype)", lifespan=lifespan)

# serve a minimal static UI
app.mount("/ui", StaticFiles(directory="backend/static", html=True), name="ui")





@app.get("/health")
def health():
    return {"status": "ok"}


def _verify_admin(request: Request):
    # Prefer short-lived session token from header or cookie
    session = request.headers.get('x-admin-session')
    if not session:
        session = request.cookies.get('jarvis_admin_session')
    if session:
        ok, actor = db.verify_admin_session(session)
        if ok:
            # Check RBAC: actor must have role 'admin' (unless master token used)
            role = db.get_user_role(actor)
            if role == 'admin' or os.environ.get('JARVIS_ADMIN_TOKEN') and request.headers.get('x-admin-token') == os.environ.get('JARVIS_ADMIN_TOKEN'):
                return True, actor
            # If no role assigned, default to admin for compatibility
            if role is None:
                return True, actor
            return False, None

    # Fallback to environment master token (legacy)
    token = request.headers.get('x-admin-token')
    env = os.environ.get('JARVIS_ADMIN_TOKEN')
    if not env:
        # no admin token configured; deny for safety
        return False, None
    if token != env:
        return False, None
    actor = request.headers.get('x-admin-actor', 'admin')
    return True, actor


def check_role(min_role: str = 'admin'):
    """Dependency factory returning a FastAPI dependency that enforces a minimum role."""
    def _dep(request: Request):
        ok, actor = _verify_admin(request)
        if not ok:
            raise HTTPException(status_code=401, detail='admin required')
        role = db.get_user_role(actor) or 'admin'
        if min_role == 'admin' and role != 'admin':
            raise HTTPException(status_code=403, detail='insufficient privileges')
        return {'actor': actor, 'role': role}
    return _dep


@app.post('/api/admin/login')
def admin_login(request: Request, payload: dict = Body(...)):
    """Exchange a configured master token for a short-lived session token.

    Payload: {"master_token": "...", "actor": "username", "ttl": 3600}
    """
    master = payload.get('master_token')
    actor = payload.get('actor', 'admin')
    ttl = int(payload.get('ttl', 3600))
    env = os.environ.get('JARVIS_ADMIN_TOKEN')
    if not env or master != env:
        raise HTTPException(status_code=401, detail='invalid master token')
    sess = db.create_admin_session(actor=actor, ttl_seconds=ttl)
    # set HttpOnly cookie with session token or jwt if available
    from fastapi import Response
    cookie_val = sess.get('jwt') or sess.get('session_token')
    resp = Response(content='{"ok": true}', media_type='application/json')
    secure = bool(os.environ.get('JARVIS_SECURE_COOKIES', '0') == '1')
    resp.set_cookie('jarvis_admin_session', cookie_val, httponly=True, secure=secure, samesite='lax', max_age=ttl, path='/')
    return resp


@app.post('/api/admin/logout')
def admin_logout(request: Request):
    # support session from cookie or header
    session = request.headers.get('x-admin-session') or request.cookies.get('jarvis_admin_session')
    if not session:
        raise HTTPException(status_code=400, detail='no session token provided')
    ok = db.revoke_admin_session(session)
    # also mark revoked for stateless tokens
    try:
        db.revoke_token(session, reason='logout')
    except Exception:
        pass
    from fastapi import Response
    resp = Response(content='{"revoked": true}', media_type='application/json')
    # delete cookie
    resp.delete_cookie('jarvis_admin_session', path='/')
    return resp


@app.get('/api/admin/sessions')
def admin_list_sessions(request: Request, limit: int = 100, offset: int = 0):
    # require admin (session or master) to list sessions
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    return db.list_admin_sessions(limit=limit, offset=offset)


@app.delete('/api/admin/sessions/{session_token}')
def admin_revoke_session(request: Request, session_token: str):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')

    # if token looks like JWT, mark as revoked; otherwise delete stateful session
    if '.' in session_token:
        # attempt to verify then revoke by sid if possible
        # extract sid by verifying JWT (but keep call minimal)
        ok_jwt, payload = db._verify_jwt(session_token)
        if not ok_jwt:
            # if not valid JWT, still store raw token in revoke list
            db.revoke_token(session_token, reason='manual_revoke')
            return {'revoked': True}
        sid = payload.get('sid')
        if sid:
            db.revoke_token(sid, actor=payload.get('actor'), reason='manual_revoke')
            try:
                settings_mod.append_audit_entry('admin', 'revoke_session', old_value=None, new_value=sid, reason='manual revoke')
            except Exception:
                pass
            return {'revoked': True}
        db.revoke_token(session_token, reason='manual_revoke')
        try:
            settings_mod.append_audit_entry('admin', 'revoke_session', old_value=None, new_value=session_token, reason='manual revoke')
        except Exception:
            pass
        return {'revoked': True}

    # otherwise try to remove from stateful sessions
    okr = db.revoke_admin_session(session_token)
    if okr:
        # also mark token as revoked for good measure
        db.revoke_token(session_token, reason='manual_revoke')
        try:
            settings_mod.append_audit_entry('admin', 'revoke_session', old_value=None, new_value=session_token, reason='manual revoke')
        except Exception:
            pass
        return {'revoked': True}
    raise HTTPException(status_code=404, detail='session not found')


@app.post('/api/admin/revoke_actor')
def admin_revoke_actor(request: Request, payload: dict = Body(...)):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    actor = payload.get('actor')
    if not actor:
        raise HTTPException(status_code=400, detail='actor required')
    removed = db.revoke_all_for_actor(actor)
    # append audit entry
    try:
        settings_mod.append_audit_entry('admin', 'revoke_actor', old_value=0, new_value=removed, reason=f'revoke_all_for_{actor}')
    except Exception:
        pass
    return {'removed_stateful': removed}


@app.get('/api/admin/session_audit')
def admin_session_audit(request: Request, limit: int = 100, offset: int = 0):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    return db.list_revoked_tokens(limit=limit, offset=offset)


@app.get('/api/admin/session_history')
def admin_session_history(request: Request, limit: int = 100, offset: int = 0, actor: str | None = None, field: str | None = None, since: int | None = None, until: int | None = None):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    # Reuse settings.get_audit_logs to return session-related audit entries (session_create, revoke_session, revoke_actor, session_cleanup)
    return settings_mod.get_audit_logs(limit=limit, offset=offset, actor=actor, field=field, since=since, until=until)


@app.get('/api/admin/users')
def admin_list_users(request: Request, limit: int = 100, offset: int = 0):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    return db.list_users(limit=limit, offset=offset)


@app.post('/api/admin/users')
def admin_create_user(request: Request, payload: dict = Body(...)):
    ok, actor = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    username = payload.get('actor')
    role = payload.get('role') or 'admin'
    if not username:
        raise HTTPException(status_code=400, detail='actor required')
    created = db.create_user(username, role)
    try:
        settings_mod.append_audit_entry(actor or 'admin', 'create_user', old_value=None, new_value={'actor': username, 'role': role}, reason='rbac create')
    except Exception:
        pass
    return {'created': True, 'actor': username, 'role': role}


@app.delete('/api/admin/users/{actor}')
def admin_delete_user(request: Request, actor: str):
    ok, user = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    removed = db.delete_user(actor)
    try:
        settings_mod.append_audit_entry(user or 'admin', 'delete_user', old_value={'actor': actor}, new_value=None, reason='rbac delete')
    except Exception:
        pass
    if removed:
        return {'deleted': True, 'actor': actor}
    raise HTTPException(status_code=404, detail='user not found')


@app.delete('/api/admin/users/{actor}')
def admin_delete_user(request: Request, actor: str):
    ok, admin_actor = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    removed = db.delete_user(actor)
    if removed:
        try:
            settings_mod.append_audit_entry(admin_actor or 'admin', 'delete_user', old_value={'actor': actor}, new_value=None, reason='rbac delete')
        except Exception:
            pass
        return {'deleted': True, 'actor': actor}
    raise HTTPException(status_code=404, detail='user not found')


@app.get('/api/admin/metrics')
def admin_metrics(request: Request):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail='admin required')
    active = db.count_active_sessions()
    revoked = db.count_revoked_tokens()
    users = len(db.list_users(limit=10000, offset=0))
    return {'active_sessions': active, 'revoked_tokens': revoked, 'users': users}


@app.post("/projects", response_model=ProjectOut)
async def create_project(request: Request, p: ProjectCreate, _auth=Depends(check_role('admin'))):
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
def get_logs(request: Request, limit: int = 200, offset: int = 0, actor: str | None = None, field: str | None = None, since: int | None = None, until: int | None = None):
    ok, _ = _verify_admin(request)
    if not ok:
        raise HTTPException(status_code=401, detail="admin token required")
    return settings_mod.get_audit_logs(limit=limit, offset=offset, actor=actor, field=field, since=since, until=until)



@app.post("/projects/{project_id}/files")
async def upload_project_file(request: Request, project_id: int, file: UploadFile = File(...), _auth=Depends(check_role('admin'))):
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
async def create_snapshot(request: Request, project_id: int, _auth=Depends(check_role('admin'))):
    try:
        sid = db.create_snapshot(project_id)
        return {"snapshot_id": sid}
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.get("/projects/{project_id}/snapshots")
def list_project_snapshots(project_id: int):
    return db.list_snapshots(project_id)


@app.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(request: Request, snapshot_id: int, _auth=Depends(check_role('admin'))):
    ok = db.restore_snapshot(snapshot_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Snapshot not found')
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


def _revoked_cleanup_loop(interval: int = 3600, retention: int = 60 * 60 * 24 * 30):
    import threading, time

    def loop():
        while True:
            try:
                try:
                    removed = db.cleanup_revoked_tokens(older_than_seconds=retention)
                    if removed:
                        try:
                            import backend.settings as settings_mod_local
                            settings_mod_local.append_audit_entry('system', 'revoked_cleanup', old_value=0, new_value=removed, reason='periodic revoked cleanup')
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def _session_cleanup_loop(interval: int = 300):
    import threading, time

    def loop():
        while True:
            try:
                try:
                    removed = db.cleanup_expired_admin_sessions()
                    # log cleanup into audit log for traceability
                    try:
                        import backend.settings as settings_mod_local
                        settings_mod_local.append_audit_entry('system', 'session_cleanup', old_value=0, new_value=removed, reason='periodic cleanup')
                    except Exception:
                        pass
                except Exception:
                    removed = 0
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


# lifespan handler sets up DB and background loops (defined earlier)


@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    # Accept a PCM16 WAV file (mono). Return the transcribed text.
    data = file.file.read()
    try:
        text = voice.transcribe_wav_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"text": text}


@app.get('/api/voice/status')
def voice_status():
    """Return status information about local STT/TTS capability."""
    info = {'vosk_installed': False, 'vosk_model_present': False, 'pyttsx3_installed': False}
    try:
        import vosk  # type: ignore
        info['vosk_installed'] = True
    except Exception:
        info['vosk_installed'] = False
    try:
        info['vosk_model_present'] = bool(voice.MODEL_DIR.exists())
    except Exception:
        info['vosk_model_present'] = False
    try:
        import pyttsx3  # type: ignore
        info['pyttsx3_installed'] = True
    except Exception:
        info['pyttsx3_installed'] = False
    return info


@app.get('/api/voice/status')
def voice_status():
    """Return presence of VOSK model and availability of pyttsx3."""
    model_present = False
    try:
        model_present = voice.MODEL_DIR.exists()
    except Exception:
        model_present = False
    tts_ok = True
    try:
        import pyttsx3  # noqa: F401
    except Exception:
        tts_ok = False
    return {'vosk_model_present': bool(model_present), 'pyttsx3_available': bool(tts_ok)}


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
