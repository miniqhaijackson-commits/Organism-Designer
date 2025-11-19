import time

from backend import db
from backend import settings as settings_mod


def test_session_creation_records_audit():
    # create session
    s = db.create_admin_session('hist_tester', ttl_seconds=5)
    token = s['session_token']
    # read audit logs and find an entry of field 'session_create' with new_value == token
    logs = settings_mod.get_audit_logs(limit=200)
    found = any(l.get('field') == 'session_create' and l.get('new_value') == token for l in logs)
    assert found
