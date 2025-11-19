import os
import time
from backend import db


def test_user_crud_and_role():
    # create user
    assert db.create_user('rbac_tester', 'viewer') is True
    role = db.get_user_role('rbac_tester')
    assert role == 'viewer'

    users = db.list_users(limit=100)
    assert any(u['actor'] == 'rbac_tester' for u in users)

    # delete user
    assert db.delete_user('rbac_tester') is True
    assert db.get_user_role('rbac_tester') is None


def test_metrics_counts_reflect_sessions_and_revokes():
    before_active = db.count_active_sessions()
    before_revoked = db.count_revoked_tokens()

    s = db.create_admin_session('metrics_user', ttl_seconds=5)
    assert 'session_token' in s
    # active sessions should increase
    after_active = db.count_active_sessions()
    assert after_active >= before_active + 1

    # revoke the session and mark revoked token
    token = s['session_token']
    assert db.revoke_admin_session(token) is True
    assert db.revoke_token(token, actor='metrics_user', reason='test_revoke') is True

    # revoked count should increase
    after_revoked = db.count_revoked_tokens()
    assert after_revoked >= before_revoked + 1

    # expired sessions cleanup should remove expired ones (run cleanup)
    time.sleep(1)
    db.cleanup_expired_admin_sessions()

