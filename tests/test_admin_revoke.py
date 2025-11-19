import os
import time

from backend import db


def test_revoke_stateful_session():
    s = db.create_admin_session('revoker', ttl_seconds=10)
    token = s['session_token']
    ok, actor = db.verify_admin_session(token)
    assert ok is True
    assert actor == 'revoker'
    # revoke
    rv = db.revoke_admin_session(token)
    assert rv is True
    ok2, _ = db.verify_admin_session(token)
    assert ok2 is False


def test_revoke_jwt_and_revocation_list(monkeypatch):
    # ensure a session key is set so JWT is produced
    monkeypatch.setenv('JARVIS_SESSION_KEY', 'test-secret-key')
    s = db.create_admin_session('jwtactor', ttl_seconds=10)
    jwt = s.get('jwt')
    assert jwt is not None
    ok, actor = db.verify_admin_session(jwt)
    assert ok is True
    # revoke by sid
    # verify underlying sid exists in DB
    sid = s['session_token']
    assert db.revoke_token(sid, actor='jwtactor', reason='test') is True
    ok2, _ = db.verify_admin_session(jwt)
    assert ok2 is False
