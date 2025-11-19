import sqlite3
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jarvis.db"


def _ensure_db_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )
    conn.commit()
    conn.close()


def create_snapshot(project_id: int) -> int:
    """Create a snapshot of a project: metadata + copy files folder."""
    import json
    import shutil
    from datetime import datetime

    proj = get_project(project_id)
    if not proj:
        raise ValueError("project not found")

    # prepare snapshot folder
    snapshots_root = DB_PATH.parent / "snapshots" / str(project_id)
    snapshots_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    snap_dir = snapshots_root / timestamp
    snap_dir.mkdir(parents=True, exist_ok=True)

    # copy project files if exist
    proj_files_folder = DB_PATH.parent / "projects" / str(project_id)
    if proj_files_folder.exists():
        try:
            shutil.copytree(str(proj_files_folder), str(snap_dir / "files"))
        except Exception:
            # if copytree fails because dest exists, fallback to copy individual files
            for p in proj_files_folder.glob("**/*"):
                if p.is_file():
                    dest = snap_dir / "files" / p.relative_to(proj_files_folder)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)

    # snapshot metadata
    meta = {"project": proj, "files": list(map(lambda r: r['filename'], list_project_files(project_id)))}

    meta_path = snap_dir / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, default=str)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS project_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, meta_json TEXT, snapshot_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("INSERT INTO project_snapshots (project_id, meta_json, snapshot_path) VALUES (?, ?, ?)", (project_id, json.dumps(meta), str(snap_dir)))
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def list_snapshots(project_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS project_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, meta_json TEXT, snapshot_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("SELECT id, project_id, snapshot_path, created_at FROM project_snapshots WHERE project_id=? ORDER BY created_at DESC", (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot(snapshot_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS project_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, meta_json TEXT, snapshot_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("SELECT id, project_id, meta_json, snapshot_path, created_at FROM project_snapshots WHERE id=?", (snapshot_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def restore_snapshot(snapshot_id: int) -> bool:
    """Restore snapshot metadata and files into project. Overwrites project files."""
    import json
    import shutil

    snap = get_snapshot(snapshot_id)
    if not snap:
        return False

    project_id = snap['project_id']
    snap_path = snap['snapshot_path']

    # restore metadata
    with open(Path(snap_path) / "meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET title=?, description=? WHERE id=?", (meta['project']['title'], meta['project'].get('description',''), project_id))
    conn.commit()
    conn.close()

    # restore files: clear current folder and copy from snapshot
    proj_files_folder = DB_PATH.parent / "projects" / str(project_id)
    if proj_files_folder.exists():
        shutil.rmtree(proj_files_folder)
    src_files = Path(snap_path) / "files"
    if src_files.exists():
        shutil.copytree(str(src_files), str(proj_files_folder))

    return True


def create_pairing(device_name: str) -> str:
    import secrets
    token = secrets.token_urlsafe(32)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO commands (command_text) VALUES (?)", (f"pairing:{device_name}",)
    )
    # store pairing metadata in a simple table
    cur.execute(
        "CREATE TABLE IF NOT EXISTS pairings (token TEXT PRIMARY KEY, device_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("INSERT INTO pairings (token, device_name) VALUES (?, ?)", (token, device_name))
    conn.commit()
    conn.close()
    return token


def verify_pairing(token: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    # ensure table exists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS pairings (token TEXT PRIMARY KEY, device_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("SELECT token FROM pairings WHERE token=?", (token,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def _ensure_admin_table(conn):
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admin_sessions (session_token TEXT PRIMARY KEY, actor TEXT, expires_at INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    # table for revoked tokens (support stateless revocation)
    cur.execute(
        "CREATE TABLE IF NOT EXISTS revoked_tokens (token TEXT PRIMARY KEY, actor TEXT, reason TEXT, revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )


def _base64url_encode(b: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode('ascii')


def _base64url_decode(s: str) -> bytes:
    import base64
    rem = len(s) % 4
    if rem:
        s += '=' * (4 - rem)
    return base64.urlsafe_b64decode(s.encode('ascii'))


def _sign_hs256(message: bytes, key: bytes) -> bytes:
    import hmac, hashlib
    return hmac.new(key, message, hashlib.sha256).digest()


def _make_jwt(sid: str, actor: str, expires_at: int) -> str:
    """Create a simple JWT-like token signed with HMAC-SHA256.

    The payload contains: sid, actor, exp.
    This function requires env var `JARVIS_SESSION_KEY` to be set.
    """
    import json, os
    key = os.environ.get('JARVIS_SESSION_KEY')
    if not key:
        raise RuntimeError('JARVIS_SESSION_KEY not configured')
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {'sid': sid, 'actor': actor, 'exp': int(expires_at)}
    seg0 = _base64url_encode(json.dumps(header, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
    seg1 = _base64url_encode(json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
    signing_input = (seg0 + '.' + seg1).encode('ascii')
    sig = _sign_hs256(signing_input, key.encode('utf-8'))
    seg2 = _base64url_encode(sig)
    return seg0 + '.' + seg1 + '.' + seg2


def _verify_jwt(token: str) -> tuple[bool, dict | None]:
    """Verify the simple JWT and return (ok, payload)"""
    import json, os, time
    key = os.environ.get('JARVIS_SESSION_KEY')
    if not key:
        return False, None
    parts = token.split('.')
    if len(parts) != 3:
        return False, None
    seg0, seg1, seg2 = parts
    try:
        signing_input = (seg0 + '.' + seg1).encode('ascii')
        expected = _sign_hs256(signing_input, key.encode('utf-8'))
        sig = _base64url_decode(seg2)
        if not hmac_compare(sig, expected):
            return False, None
        payload_json = _base64url_decode(seg1).decode('utf-8')
        payload = json.loads(payload_json)
        if int(payload.get('exp', 0)) < int(time.time()):
            return False, None
        return True, payload
    except Exception:
        return False, None


def hmac_compare(a: bytes, b: bytes) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


def create_admin_session(actor: str, ttl_seconds: int = 3600) -> dict:
    """Create a short-lived admin session token and return metadata."""
    import secrets, time

    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + int(ttl_seconds)
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO admin_sessions (session_token, actor, expires_at) VALUES (?, ?, ?)", (token, actor, expires))
    conn.commit()
    conn.close()

    # If a session signing key is configured, also emit a signed JWT for convenience
    import os
    jwt_val = None
    if os.environ.get('JARVIS_SESSION_KEY'):
        try:
            jwt_val = _make_jwt(token, actor, expires)
        except Exception:
            jwt_val = None

    out = {"session_token": token, "actor": actor, "expires_at": expires}
    if jwt_val:
        out['jwt'] = jwt_val
    # append audit entry for creation
    try:
        import backend.settings as settings_mod_local
        settings_mod_local.append_audit_entry(actor, 'session_create', old_value=None, new_value=token, reason='session created')
    except Exception:
        pass
    return out


def verify_admin_session(session_token: str) -> tuple[bool, str | None]:
    """Return (True, actor) if session is valid and not expired."""
    import time

    # If the token looks like a JWT (contains '.'), try JWT verification first
    if isinstance(session_token, str) and '.' in session_token:
        ok, payload = _verify_jwt(session_token)
        if ok:
            # ensure session id present in DB and not expired
            sid = payload.get('sid')
            if not sid:
                return False, None
            # Check revocation list first
            if is_token_revoked(sid):
                return False, None
            conn = get_conn()
            _ensure_admin_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT session_token, actor, expires_at FROM admin_sessions WHERE session_token=?", (sid,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return False, None
            if int(row['expires_at']) < int(time.time()):
                return False, None
            return True, row['actor']

    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT session_token, actor, expires_at FROM admin_sessions WHERE session_token=?", (session_token,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False, None
    if int(row['expires_at']) < int(time.time()):
        return False, None
    return True, row['actor']


def revoke_admin_session(session_token: str) -> bool:
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM admin_sessions WHERE session_token=?", (session_token,))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return bool(changed)


def revoke_token(token: str, actor: str | None = None, reason: str | None = None) -> bool:
    """Mark a token as revoked (for JWT/stateless flows).

    Returns True if inserted (or already present), False on error.
    """
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR REPLACE INTO revoked_tokens (token, actor, reason) VALUES (?, ?, ?)", (token, actor, reason))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def is_token_revoked(token: str) -> bool:
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT token FROM revoked_tokens WHERE token=?", (token,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def revoke_all_for_actor(actor: str) -> int:
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM admin_sessions WHERE actor=?", (actor,))
    removed_stateful = cur.rowcount
    # Mark any existing sessions in DB as revoked as well for audit
    cur.execute("INSERT INTO revoked_tokens (token, actor, reason) SELECT session_token, actor, 'revoke_all' FROM admin_sessions WHERE actor=?", (actor,))
    conn.commit()
    conn.close()
    return removed_stateful


def list_revoked_tokens(limit: int = 100, offset: int = 0):
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT token, actor, reason, revoked_at FROM revoked_tokens ORDER BY revoked_at DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_revoked_tokens(older_than_seconds: int = 60 * 60 * 24 * 30) -> int:
    """Remove revoked token records older than `older_than_seconds` and return number removed."""
    import time
    cutoff = int(time.time()) - int(older_than_seconds)
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM revoked_tokens WHERE revoked_at<?", (cutoff,))
    removed = cur.rowcount
    conn.commit()
    conn.close()
    return removed


def cleanup_expired_admin_sessions() -> int:
    """Delete expired admin sessions and return the number removed."""
    import time
    now = int(time.time())
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM admin_sessions WHERE expires_at<?", (now,))
    removed = cur.rowcount
    conn.commit()
    conn.close()
    return removed


def list_admin_sessions(limit: int = 100, offset: int = 0):
    """Return non-expired admin sessions (most recent first)."""
    import time
    now = int(time.time())
    conn = get_conn()
    _ensure_admin_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT session_token, actor, expires_at, created_at FROM admin_sessions WHERE expires_at>? ORDER BY created_at DESC LIMIT ? OFFSET ?", (now, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _row_to_session(row):
    return {"session_token": row['session_token'], 'actor': row['actor'], 'expires_at': row['expires_at'], 'created_at': row.get('created_at')}


def add_project_file(project_id: int, filename: str, content: bytes) -> str:
    # ensure project folder
    folder = DB_PATH.parent / "projects" / str(project_id)
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / filename
    with open(file_path, "wb") as f:
        f.write(content)

    # store metadata
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, filename TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("INSERT INTO project_files (project_id, filename) VALUES (?, ?)", (project_id, filename))
    conn.commit()
    conn.close()
    return str(file_path)


def list_project_files(project_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, filename TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.execute("SELECT id, filename FROM project_files WHERE project_id=? ORDER BY created_at DESC", (project_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_project(title: str, description: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (title, description) VALUES (?, ?)", (title, description))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def list_projects() -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description FROM projects ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description FROM projects WHERE id=?", (project_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_command(command_text: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO commands (command_text) VALUES (?)", (command_text,))
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return cid
