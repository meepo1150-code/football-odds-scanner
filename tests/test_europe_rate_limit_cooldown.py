import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

from odds_scanner import europe_pinnacle_discovery as collector


def test_retry_after_respects_provider_and_minimum():
    now = datetime(2026, 10, 3, 13, tzinfo=timezone.utc)
    for header, expected in [('5', 3600), ('7200', 7200),
                             ('Sat, 03 Oct 2026 15:00:00 GMT', 7200),
                             ('invalid', 3600)]:
        error = HTTPError('https://example.test', 429, 'limited', {'Retry-After': header}, None)
        assert collector._rate_limit_until(error, now) == (now + timedelta(seconds=expected)).isoformat()


def test_rate_limit_stops_batches_and_next_run_without_touching_raw(tmp_path, monkeypatch):
    monkeypatch.setenv(collector.ENV_KEY, 'test-only')
    monkeypatch.setenv('RESEARCH_V2_FORCE_RUN', 'true')
    target = tmp_path / collector.TARGET_PATH
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'tournaments': [{'tournament_id': n} for n in range(12)]}))
    raw = tmp_path / collector.SNAPSHOT_PATH
    raw.parent.mkdir(parents=True)
    raw.write_text('{"fixture_id":"preserve-forensic-record"}\n')
    before = raw.read_bytes()
    calls = []

    def get(path, *args):
        calls.append(path)
        if path == '/account':
            return {}
        raise HTTPError('https://example.test', 429, 'limited', {'Retry-After': '7200'}, None)

    monkeypatch.setattr(collector, '_get', get)
    monkeypatch.setattr(collector, 'summarize_account', lambda _: {'request_remaining': 200})
    monkeypatch.setattr(collector.time, 'sleep', lambda _: (_ for _ in ()).throw(AssertionError('must not retry or start another batch')))
    report = collector.run(tmp_path)
    assert calls == ['/account', '/odds-by-tournaments']
    assert report['requests_used'] == 1
    assert report['rate_limit_retries'] == 0
    assert report['data_source_health'] == 'RATE_LIMITED'
    for _ in range(3):
        report = collector.run(tmp_path)
        assert report['requests_used'] == 0
        assert report['data_source_health'] == 'RATE_LIMITED_COOLDOWN'
    assert calls == ['/account', '/odds-by-tournaments']
    assert raw.read_bytes() == before
