from fastapi.testclient import TestClient
import time
import os

from backend import app, db

client = TestClient(app.app)


def make_session(actor, ttl=60):
    s = db.create_admin_session(actor, ttl_seconds=ttl)
    return s.get('session_token') or s.get('jwt')


def test_viewer_cannot_create_project_but_admin_can():
    # create viewer user
    name = f'viewer_{int(time.time())}'
    assert db.create_user(name, 'viewer') is True
    # create sessions
    viewer_token = make_session(name, ttl=60)
    admin_token = make_session('integration_admin', ttl=60)

    # viewer attempt should be rejected (403)
    res = client.post('/projects', json={'title': 'X', 'description': 'desc'}, headers={'x-admin-session': viewer_token})
    assert res.status_code in (401, 403)

    # admin attempt should succeed
    res2 = client.post('/projects', json={'title': 'Admin Project', 'description': 'ok'}, headers={'x-admin-session': admin_token})
    assert res2.status_code == 200
    data = res2.json()
    assert data['title'] == 'Admin Project'

    # cleanup
    db.delete_user(name)


def test_stt_tts_endpoints_available():
    # TTS: should return audio when pyttsx3 available or error if not
    res = client.post('/tts', data={'text': 'hello world'})
    # either OK (200/206) or 400 if engine missing; accept both
    assert res.status_code in (200, 400)

    # STT: without a file expect 422 or bad request; just test endpoint responds
    # create a tiny empty wav to post (invalid) to ensure an error path
    files = {'file': ('x.wav', b'RIFF....', 'audio/wav')}
    res2 = client.post('/transcribe', files=files)
    assert res2.status_code in (200, 400, 422)
