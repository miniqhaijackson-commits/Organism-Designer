import time
import os

from backend import db


def test_create_and_verify_and_revoke_session():
    # create a session with short ttl
    s = db.create_admin_session('tester', ttl_seconds=5)
    assert 'session_token' in s
    token = s['session_token']

    ok, actor = db.verify_admin_session(token)
    assert ok is True
    assert actor == 'tester'

    # revoke and ensure it's gone
    revoked = db.revoke_admin_session(token)
    assert revoked is True
    ok2, _ = db.verify_admin_session(token)
    assert ok2 is False


def test_session_expiry():
    # create session with 1 second ttl
    s = db.create_admin_session('expirer', ttl_seconds=1)
    token = s['session_token']
    ok, _ = db.verify_admin_session(token)
    assert ok is True
    # wait for expiry (sleep a bit longer to account for integer-second storage)
    time.sleep(2)
    ok2, _ = db.verify_admin_session(token)
    assert ok2 is False
