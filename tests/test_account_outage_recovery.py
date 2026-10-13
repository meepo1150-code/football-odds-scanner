import json
import urllib.error

import pytest

from odds_scanner import oddspapi_quota_health as quota
from odds_scanner import europe_pinnacle_discovery as collector
from odds_scanner import propline_research_v2 as propline
from odds_scanner.scan_health import HISTORY, rows
from test_collector_observation_contract import setup


def http(code):
    return urllib.error.HTTPError('https://provider.invalid/?apiKey=secret', code, 'failure', {}, None)


def test_transient_account_retry_is_unmetered_and_bounded(monkeypatch):
    calls = []
    delays = []
    monkeypatch.setattr(quota.time, 'sleep', delays.append)
    def get(path, key):
        calls.append(path)
        if len(calls) < 3:
            raise http(500)
        return {'live': True}
    diagnostics = {}
    assert quota.read_account('secret', getter=get, diagnostics=diagnostics) == {'live': True}
    assert calls == ['/account'] * 3 and delays == [2, 4]
    assert diagnostics['account_requests_attempted'] == 3
    assert diagnostics['account_endpoint_metered'] is False
    assert 'secret' not in json.dumps(diagnostics)


@pytest.mark.parametrize('code', [401, 403, 429])
def test_account_auth_or_rate_limit_never_retried(monkeypatch, code):
    def no_sleep(_):
        raise AssertionError('must not retry')
    monkeypatch.setattr(quota.time, 'sleep', no_sleep)
    diagnostics = {}
    with pytest.raises(urllib.error.HTTPError):
        quota.read_account('secret', getter=lambda *a: (_ for _ in ()).throw(http(code)), diagnostics=diagnostics)
    assert diagnostics['account_requests_attempted'] == 1


def test_persistent_account_500_never_uses_cached_quota_or_odds(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(quota.time, 'sleep', lambda _: None)
    p = tmp_path/quota.REPORT_PATH
    p.write_text(json.dumps({'request_remaining': 200, 'status': 'QUOTA_AVAILABLE'}))
    calls = []
    def get(path, *args):
        calls.append(path)
        assert path == '/account'
        raise http(500)
    monkeypatch.setattr(collector, '_get', get)
    report = collector.run(tmp_path)
    assert calls == ['/account'] * 3
    assert report['requests_used'] == 0
    assert report['status'] == 'SKIPPED_QUOTA_HEALTH_UNAVAILABLE'
    receipt = rows(tmp_path/HISTORY)[-1]
    assert receipt['status'] == 'FAIL' and receipt['api_error_count'] == 1
    assert 'secret' not in (tmp_path/HISTORY).read_text()
    assert not (tmp_path/collector.SNAPSHOT_PATH).exists()


def test_recovered_account_allows_only_original_market_budget(tmp_path, monkeypatch):
    _, fixture = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(quota.time, 'sleep', lambda _: None)
    calls = []
    def get(path, *args):
        calls.append(path)
        if path == '/account':
            if len(calls) == 1:
                raise http(503)
            return {}
        return [fixture]
    monkeypatch.setattr(collector, '_get', get)
    report = collector.run(tmp_path)
    assert calls == ['/account', '/account', '/odds-by-tournaments']
    assert report['requests_used'] == 1 and report['strict_snapshots_this_run'] == 1
    assert report['account_requests_attempted'] == 2


def test_unmapped_fallback_reports_configuration_without_fake_zero(tmp_path, monkeypatch):
    from odds_scanner import propline_provider as provider
    monkeypatch.setenv(provider.ENV_KEY, 'secret')
    monkeypatch.setattr(provider, '_get', lambda *a: (_ for _ in ()).throw(AssertionError('unmapped provider requested')))
    report = propline.run(tmp_path)
    assert report['status'] == 'MASTER_PROVIDER_MAPPING_UNAVAILABLE'
    assert report['http_requests_attempted'] == 0 and report['requests_used'] == 0
    receipt = rows(tmp_path/HISTORY)[-1]
    assert receipt['fixtures_found'] is None and receipt['api_error_count'] == 0
    assert receipt['status'] == 'FAIL'
