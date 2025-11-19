import time
import json
from pathlib import Path

from backend import settings as settings_mod


def _write_log_lines(lines):
    p = Path(__file__).resolve().parent.parent / 'data' / 'jarvis_settings.log'
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False) + '\n')


def test_log_filtering_by_actor_and_field():
    now = int(time.time())
    lines = [
        {'timestamp': now - 100, 'actor': 'alice', 'field': 'volume', 'old_value': 0, 'new_value': 1},
        {'timestamp': now - 50, 'actor': 'bob', 'field': 'theme', 'old_value': 'light', 'new_value': 'dark'},
        {'timestamp': now - 10, 'actor': 'alice', 'field': 'theme', 'old_value': 'dark', 'new_value': 'light'},
    ]
    _write_log_lines(lines)

    out = settings_mod.get_audit_logs(limit=10, actor='alice')
    assert len(out) == 2

    out2 = settings_mod.get_audit_logs(limit=10, field='theme')
    assert len(out2) == 2


def test_log_time_range_and_pagination():
    now = int(time.time())
    lines = []
    for i in range(10):
        lines.append({'timestamp': now - i, 'actor': 'x', 'field': f'f{i}', 'old_value': None, 'new_value': i})
    _write_log_lines(lines)

    # newest first, limit and offset
    page1 = settings_mod.get_audit_logs(limit=3, offset=0)
    page2 = settings_mod.get_audit_logs(limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0]['timestamp'] >= page2[0]['timestamp']

    # time range
    since = now - 2
    r = settings_mod.get_audit_logs(limit=10, since=since)
    assert all(int(e['timestamp']) >= since for e in r)
