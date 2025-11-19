from flask import Flask, render_template_string, jsonify, request, abort
import json
import datetime
import os
import threading
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

# Basic hardened Flask settings app
app = Flask(__name__)

WORKDIR = Path(__file__).resolve().parent
SETTINGS_FILE = WORKDIR / "jarvis_settings.json"
AUDIT_LOG = WORKDIR / "jarvis_settings.log"

# Simple in-process lock to serialize writes
_write_lock = threading.RLock()

# Admin key for reading audit logs. Set via environment variable for safety.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", None)


def _default_settings():
    return {
        "voiceWakeWord": "J.A.R.V.I.S",
        "alwaysListening": True,
        "autoSaveInterval": "Every 5 minutes",
        "dataEncryption": True,
        "lawCompliance": True,
        "responseStyle": "Professional",
        "learningMode": True,
        "proactiveAssistance": False,
        "bypassRestrictions": False,
        "autoDiscoverDevices": True,
        "dataCollection": True,
        "cameraAccess": False,
        "locationServices": True,
        "memoryUsage": "2.4 GB / 16 GB",
        "storageUsed": "847 MB",
        "lastSystemCheck": "2 hours ago",
        "version": "v2.1.4",
        "lastUpdated": datetime.datetime.now().strftime("%B %d, %Y")
    }


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        settings = _default_settings()
        # create file on first load
        _atomic_write_json(SETTINGS_FILE, settings)
        return settings
    except Exception:
        # Corrupt file fallback
        return _default_settings()


def _atomic_write_json(path: Path, obj: dict):
    # Write to temp file in same directory then atomically replace
    tmp_dir = path.parent
    with NamedTemporaryFile("w", delete=False, dir=tmp_dir, encoding="utf-8") as tf:
        json.dump(obj, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        tmpname = tf.name
    os.replace(tmpname, str(path))


def _append_audit(entry: dict):
    # Append newline-delimited JSON (NDJSON) for auditability
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        # best-effort logging; don't raise to caller
        pass


def save_settings_field(actor: str, key: str, value) -> dict:
    """Validate, audit and atomically save a single settings field.

    Returns the updated settings dict on success.
    Raises ValueError on validation failure.
    """
    allowed_keys = {
        "voiceWakeWord": str,
        "alwaysListening": bool,
        "autoSaveInterval": str,
        "dataEncryption": bool,
        "lawCompliance": bool,
        "responseStyle": str,
        "learningMode": bool,
        "proactiveAssistance": bool,
        "bypassRestrictions": bool,
        "autoDiscoverDevices": bool,
        "dataCollection": bool,
        "cameraAccess": bool,
        "locationServices": bool
    }

    if key not in allowed_keys:
        raise ValueError("Unsupported settings key")

    expected_type = allowed_keys[key]
    # Attempt to coerce simple types from JSON values
    if expected_type is bool and isinstance(value, (str, int)):
        # Accept common truthy/falsy representations
        if isinstance(value, str):
            v_low = value.lower()
            if v_low in ("true", "1", "yes", "on"):
                value = True
            elif v_low in ("false", "0", "no", "off"):
                value = False
        else:
            value = bool(value)

    if not isinstance(value, expected_type):
        raise ValueError(f"Invalid type for {key}: expected {expected_type.__name__}")

    # Enforce safety: if lawCompliance is True then bypassRestrictions cannot be enabled
    settings = load_settings()
    old = settings.get(key)

    if key == "bypassRestrictions" and value is True and settings.get("lawCompliance", True):
        raise ValueError("Cannot enable bypassRestrictions while lawCompliance is enabled")

    # Write with lock and atomic replace
    with _write_lock:
        settings[key] = value
        settings["lastUpdated"] = datetime.datetime.now().strftime("%B %d, %Y %H:%M:%S")
        _atomic_write_json(SETTINGS_FILE, settings)

        # Audit entry
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "actor": actor,
            "key": key,
            "old": old,
            "new": value
        }
        _append_audit(entry)

    return settings


# HTML (kept minimal and derived from provided template)
HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><title>J.A.R.V.I.S Settings</title>
<style>body{font-family:Arial,Helvetica,sans-serif;background:#0a0a0a;color:#fff;padding:20px}label{display:block;margin:8px 0}</style>
</head><body>
<h1>J.A.R.V.I.S Settings</h1>
<div id="content">Loading…</div>
<script>
async function fetchSettings(){
  const r = await fetch('/settings');
  const s = await r.json();
  const keys = ['voiceWakeWord','alwaysListening','autoSaveInterval','dataEncryption','lawCompliance','responseStyle','learningMode','proactiveAssistance','bypassRestrictions','autoDiscoverDevices','dataCollection','cameraAccess','locationServices','memoryUsage','storageUsed','lastSystemCheck','version','lastUpdated'];
  let html = '<form id="f">';
  for(const k of keys){
    const v = s[k];
    if(typeof v === 'boolean'){
      html += `<label>${k}: <input type="checkbox" name="${k}" ${v? 'checked':''}></label>`;
    } else if(k==='responseStyle'){
      html += `<label>${k}: <select name="${k}"><option>Professional</option><option>Casual</option><option>Technical</option><option>Concise</option></select></label>`;
    } else {
      html += `<label>${k}: <input name="${k}" value="${String(v).replace(/\"/g,'&quot;')}"></label>`;
    }
  }
  html += '<button type="submit">Save</button></form>';
  document.getElementById('content').innerHTML = html;
  document.getElementById('f').addEventListener('submit', async (ev)=>{ev.preventDefault(); const fm=new FormData(ev.target); for(const [k,v] of fm.entries()){ let val=v; if(ev.target[k].type==='checkbox') val=ev.target[k].checked; await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:k,value:val,actor:'web-ui'})}).then(r=>r.json()).then(d=>{if(!d.ok)alert('Save failed: '+d.error)}); } alert('Saved'); location.reload(); });
}
fetchSettings();
</script>
</body></html>
"""


@app.route('/')
def home():
    return render_template_string(HTML)


@app.route('/settings')
def settings():
    return jsonify(load_settings())


@app.route('/save', methods=['POST'])
def save():
    data = request.get_json(silent=True)
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    actor = data.get('actor') or request.headers.get('X-User', 'unknown')
    try:
        updated = save_settings_field(actor, data['key'], data['value'])
        return jsonify({"ok": True, "settings": updated})
    except ValueError as e:
        # Log the failed attempt
        _append_audit({
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "actor": actor,
            "key": data.get('key'),
            "old": None,
            "new": data.get('value'),
            "error": str(e)
        })
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": "internal_error"}), 500


@app.route('/api/logs')
def api_logs():
    # Admin-only: require ADMIN_API_KEY header
    key = request.headers.get('X-ADMIN-KEY')
    if ADMIN_API_KEY and key != ADMIN_API_KEY:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # Read last N log lines
    try:
        n = int(request.args.get('n', '200'))
    except Exception:
        n = 200

    if not AUDIT_LOG.exists():
        return jsonify({"ok": True, "logs": []})

    # Read file efficiently from end
    lines = []
    with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except Exception:
                    # skip malformed line
                    continue

    return jsonify({"ok": True, "logs": lines[-n:]})


def _background_status_update_loop():
    import random
    while True:
        time.sleep(30)
        try:
            with _write_lock:
                settings = load_settings()
                settings["memoryUsage"] = f"{random.uniform(1.5, 3.5):.1f} GB / 16 GB"
                settings["storageUsed"] = f"{random.randint(700, 1000)} MB"
                settings["lastSystemCheck"] = random.choice(["30 minutes ago", "1 hour ago", "45 minutes ago", "2 hours ago"])
                _atomic_write_json(SETTINGS_FILE, settings)
        except Exception:
            pass


threading.Thread(target=_background_status_update_loop, daemon=True).start()


if __name__ == '__main__':
    # Only for local development. In production run with a WSGI server.
    app.run(host='0.0.0.0', port=5001, debug=False)
