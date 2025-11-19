import os
import json
import time
from pathlib import Path
import tempfile

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_PATH = DATA_DIR / 'jarvis_settings.json'
LOG_PATH = DATA_DIR / 'jarvis_settings.log'


def _read_json_file(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # If corrupted, return empty dict but keep file for forensics
        return {}


def load_settings():
    return _read_json_file(SETTINGS_PATH)


def save_settings_atomic(new_settings: dict, actor: str = "unknown", reason: str | None = None):
    """Atomically save `new_settings` to `SETTINGS_PATH` and append per-field audit entries.

    Each audit entry is a JSON line with: timestamp, actor, reason, field, old_value, new_value
    """
    old = load_settings()

    # compute changed keys (including added/removed)
    changed = []
    keys = set(old.keys()) | set(new_settings.keys())
    for k in keys:
        old_v = old.get(k)
        new_v = new_settings.get(k)
        if old_v != new_v:
            changed.append((k, old_v, new_v))

    # write new settings atomically in same directory
    tmp = None
    try:
        dirpath = SETTINGS_PATH.parent
        with tempfile.NamedTemporaryFile('w', dir=dirpath, delete=False, encoding='utf-8') as tf:
            tmp = Path(tf.name)
            json.dump(new_settings, tf, ensure_ascii=False, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
        # atomic replace
        tmp.replace(SETTINGS_PATH)
    finally:
        if tmp and tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass

    # append audit log entries
    ts = int(time.time())
    entries = []
    for field, old_v, new_v in changed:
        entry = {
            'timestamp': ts,
            'actor': actor,
            'reason': reason,
            'field': field,
            'old_value': old_v,
            'new_value': new_v,
        }
        entries.append(entry)

    if entries:
        with LOG_PATH.open('a', encoding='utf-8') as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')

    return {'changed': len(entries)}


def append_audit_entry(actor: str, field: str, old_value, new_value, reason: str | None = None):
    ts = int(time.time())
    entry = {
        'timestamp': ts,
        'actor': actor,
        'reason': reason,
        'field': field,
        'old_value': old_value,
        'new_value': new_value,
    }
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def get_audit_logs(limit: int = 100, offset: int = 0, actor: str | None = None, field: str | None = None, since: int | None = None, until: int | None = None):
    """Return audit log entries with basic filtering and pagination.

    - `limit` and `offset` implement pagination (most recent first ordering).
    - `actor` and `field` filter by exact match.
    - `since` and `until` are Unix timestamps (seconds) to filter time range inclusive.
    """
    if not LOG_PATH.exists():
        return []
    entries = []
    with LOG_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            entries.append(e)

    # newest first
    entries = list(reversed(entries))

    def keep(e):
        if actor and str(e.get('actor')) != str(actor):
            return False
        if field and str(e.get('field')) != str(field):
            return False
        ts = int(e.get('timestamp', 0))
        if since is not None and ts < int(since):
            return False
        if until is not None and ts > int(until):
            return False
        return True

    filtered = [e for e in entries if keep(e)]
    return filtered[offset: offset + limit]
