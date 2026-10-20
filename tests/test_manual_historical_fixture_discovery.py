"""Offline contract tests for day-scoped native OddsPapi fixture discovery."""
import argparse
import json
from datetime import datetime, timezone

import pytest

from odds_scanner.historical_manual import planner, runner
from odds_scanner.historical_manual.safety import HttpClient, StopPilot

NOW = datetime(2026, 10, 19, 4, tzinfo=timezone.utc)
ENV = {
    'GITHUB_EVENT_NAME': 'workflow_dispatch',
    'GITHUB_REF': 'refs/heads/main',
    'PILOT_ENVIRONMENT': 'historical-research',
    'HISTORICAL_ODDSPAPI_KEY': 'fixture-test-research',
    'ACCOUNT_PROBE_KEY': 'fixture-test-production',
}


def options(**kwargs):
    return argparse.Namespace(**dict(dict(
        start_day='2026-09-04', end_day='2026-09-04',
        times='15:00,18:00,21:00,00:00', bookmakers='pinnacle',
        mode='recover', confirm_live_requests=True,
        allow_growing_history=True, max_runtime_seconds=8400),
        **kwargs))


def fixture(**kwargs):
    return dict(dict(
        fixtureId='id984', tournamentId=17, statusId=2,
        participant1Name='Verified Home', participant2Name='Verified Away',
        startTime='2026-09-04T19:00:00Z',
    ), **kwargs)


def fake_accounts(key):
    return dict(current_subscription_id=key, subscriptions=[dict(
        subscription_id=key, is_active=True, request_limit=250,
        request_count=0, sport_ids=[10],
        bookmakers={'pinnacle': {}, 'bet365': {}})])


def run(tmp_path, *, mode='recover', confirm=True, provider_rows=None, monkeypatch=None, **selected):
    if monkeypatch is not None:
        from odds_scanner import master_schedule_plan
        monkeypatch.setattr(master_schedule_plan, 'registry', lambda: [
            dict(tournament_id=17, tournament_name='Verified League')])
    calls = []
    responses = [fixture()] if provider_rows is None else provider_rows

    def factory(key):
        def request(path, params):
            calls.append((key, path, params))
            if path == '/account':
                return 200, {}, json.dumps(fake_accounts(key)).encode()
            if path == '/fixtures':
                return 200, {}, json.dumps(responses).encode()
            if path == '/historical-odds':
                return 200, {}, json.dumps(dict(
                    fixtureId=params['fixtureId'], bookmakers={})).encode()
            raise AssertionError('Unexpected HTTP endpoint: '+path)
        return request

    report = runner.execute(options(mode=mode, confirm_live_requests=confirm, **selected),
        root=tmp_path, clock=lambda: NOW, sleeper=lambda _: None,
        client_factory=factory,
        health_reader=lambda: dict(generated_at=NOW.isoformat(),
                                   status='PASS', issues=[]),
        environ=ENV)
    return report, calls


def test_recover_discovers_native_fixture_without_previous_snapshot(tmp_path, monkeypatch):
    report, calls = run(tmp_path, monkeypatch=monkeypatch)
    assert report['status'] == 'COMPLETED'
    assert report['fixture_discovery_requests'] == 1
    assert report['historical_requests'] == 1
    assert report['plan']['unique_fixtures'] == 1
    assert report['plan']['fixture_bookmaker_pairs'] == 1
    discovery = [(key, p, args) for key, p, args in calls if p == '/fixtures']
    assert len(discovery) == 1
    key, _, params = discovery[0]
    assert key == ENV['HISTORICAL_ODDSPAPI_KEY']
    assert params['sportId'] == 10 and params['statusId'] == 2
    assert params['from'] == '2026-09-03T23:00:00Z'
    assert params['to'] == '2026-09-04T23:00:00Z'
    assert params['to'] != params['from']
    assert all(p != '/fixtures' for key, p, _ in calls if key == ENV['ACCOUNT_PROBE_KEY'])
    assert [p for _, p, _ in calls].count('/historical-odds') == 1
    evidence = json.loads((tmp_path / runner.OUT / 'manifest.json').read_text())
    c = evidence['candidates'][0]
    assert c['fixture_id'] == 'id984'
    assert c['evidence'][0]['mapping_source'] == 'ODDSPAPI_NATIVE_FIXTURES_RECEIPT'
    assert c['observations'] == []
    assert (tmp_path / runner.OUT / 'discovery_receipts/2026-09-04.json').exists()


def test_fixture_discovery_receipt_reused_without_api_requests(tmp_path, monkeypatch):
    report, calls = run(tmp_path, monkeypatch=monkeypatch)
    assert report['status'] == 'COMPLETED'
    again, second_calls = run(tmp_path, mode='cache-only', confirm=False,
                              monkeypatch=monkeypatch)
    assert again['status'] == 'COMPLETED'
    assert again['fixture_discovery_requests'] == 0
    assert second_calls == []
    # Re-running recover does not rediscover existing exact fixture IDs.
    repeat, repeat_calls = run(tmp_path, monkeypatch=monkeypatch)
    assert repeat['status'] == 'COMPLETED'
    assert all(path != '/fixtures' for _, path, _ in repeat_calls)


def test_plan_and_unconfirmed_recover_never_discover(tmp_path, monkeypatch):
    for mode, confirm in [('plan', True), ('cache-only', False), ('recover', False)]:
        report, calls = run(tmp_path, mode=mode, confirm=confirm,
                            monkeypatch=monkeypatch)
        assert report['status'] == 'NO_VERIFIED_FIXTURES'
        assert report['total_http_requests'] == 0
        assert calls == []


def test_unknown_competition_is_not_mapped_or_priced(tmp_path, monkeypatch):
    report, calls = run(tmp_path, provider_rows=[fixture(tournamentId=999)],
                        monkeypatch=monkeypatch)
    assert report['status'] == 'NO_VERIFIED_FIXTURES'
    assert report['fixture_discovery_requests'] == 1
    assert report['fixture_discovery_days'][0]['returned'] == 1
    assert report['fixture_discovery_days'][0]['approved_finished'] == 0
    assert not any(path == '/historical-odds' for _, path, _ in calls)
    repeat, subsequent = run(tmp_path, monkeypatch=monkeypatch)
    assert repeat['fixture_discovery_requests'] == 0
    assert not any(path == '/fixtures' for _, path, _ in subsequent)


def test_tampered_native_fixture_receipt_fails_closed(tmp_path, monkeypatch):
    run(tmp_path, provider_rows=[fixture(tournamentId=999)],
        monkeypatch=monkeypatch)
    receipt = tmp_path / runner.CACHE / 'fixture_discovery_receipts/2026-09-04.json'
    text = receipt.read_text().replace('Verified Home', 'Falsified Home')
    receipt.write_text(text)
    with pytest.raises(ValueError, match='MANUAL_FIXTURE_RECEIPT_HASH_MISMATCH'):
        planner.build(tmp_path, '2026-09-04', '2026-09-04',
                      '15:00', 'pinnacle', NOW)


def test_transport_allows_only_explicit_read_endpoints():
    class Empty:
        pass
    client = HttpClient('dummy')
    with pytest.raises(StopPilot, match='ENDPOINT_NOT_ALLOWED'):
        client('/odds', {})


def test_multi_day_discovers_only_days_without_existing_evidence(tmp_path, monkeypatch):
    original = tmp_path / planner.SOURCES[0]
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text(json.dumps(dict(
        fixture_id='id987', bookmaker='pinnacle', home='Home7', away='Away7',
        league='Verified League', kickoff='2026-09-07T18:00:00Z',
        observed_at='2026-09-07T07:00:00Z',
        source_semantics='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED'))+'\n')
    report, calls = run(tmp_path, monkeypatch=monkeypatch,
                        end_day='2026-09-07')
    fixture_calls = [params for _, path, params in calls if path == '/fixtures']
    assert len(fixture_calls) == 3
    assert {params['from'] for params in fixture_calls} == {
        '2026-09-03T23:00:00Z',
        '2026-09-04T23:00:00Z',
        '2026-09-05T23:00:00Z',
    }
    assert report['fixture_discovery_existing_evidence_days'] == 1
    assert report['plan']['unique_fixtures'] == 2


def test_thousand_row_discovery_is_split_and_only_completed_rows_become_candidates(
        tmp_path, monkeypatch):
    from odds_scanner import master_schedule_plan
    monkeypatch.setattr(master_schedule_plan, 'registry', lambda: [
        dict(tournament_id=17, tournament_name='Verified League')])
    calls = []
    oversized = [fixture(fixtureId='id'+str(10000+i), tournamentId=999)
                 for i in range(1000)]
    approved = fixture()
    def factory(key):
        def request(path, params):
            calls.append((key, path, params))
            if path == '/account':
                return 200, {}, json.dumps(fake_accounts(key)).encode()
            if path == '/fixtures':
                if params['from'] == '2026-08-29T23:00:00Z':
                    return 200, {}, json.dumps(oversized).encode()
                if params['from'] == '2026-08-30T11:00:00Z':
                    return 200, {}, json.dumps([approved]).encode()
                return 200, {}, json.dumps([approved]).encode()
            if path == '/historical-odds':
                return 200, {}, json.dumps(dict(
                    fixtureId=params['fixtureId'], bookmakers={})).encode()
            raise AssertionError(path)
        return request
    result = runner.execute(options(start_day='2026-08-30',
        end_day='2026-08-30'), root=tmp_path, clock=lambda: NOW,
        sleeper=lambda _: None, client_factory=factory,
        health_reader=lambda: dict(generated_at=NOW.isoformat(),
                                   status='PASS', issues=[]),
        environ=ENV)
    assert result['status'] == 'COMPLETED'
    assert result['fixture_discovery_requests'] == 3
    assert result['historical_requests'] == 1
    assert result['plan']['unique_fixtures'] == 1
    assert len(result['fixture_discovery_split_windows']) == 1
    assert len([p for _, p, _ in calls if p == '/fixtures']) == 3
    receipt = json.loads((tmp_path / runner.CACHE /
        'fixture_discovery_receipts/2026-08-30.json').read_text())
    assert receipt['completeness'] == 'SPLIT_WINDOWS_BELOW_1000_ROWS'
    assert len(receipt['payload']) == 1
    assert (tmp_path / runner.OUT / 'discovery_receipts/2026-08-30.json').exists()


def test_provider_still_truncated_at_short_window_stops_without_publishing(tmp_path, monkeypatch):
    from odds_scanner import master_schedule_plan
    monkeypatch.setattr(master_schedule_plan, 'registry', lambda: [
        dict(tournament_id=17, tournament_name='Verified League')])
    huge = [fixture(fixtureId='id'+str(10000+i), tournamentId=999)
            for i in range(1000)]
    calls = []
    def factory(key):
        def request(path, params):
            calls.append(path)
            if path == '/account':
                return 200, {}, json.dumps(fake_accounts(key)).encode()
            if path == '/fixtures':
                return 200, {}, json.dumps(huge).encode()
            raise AssertionError(path)
        return request
    result = runner.execute(options(), root=tmp_path, clock=lambda: NOW,
        sleeper=lambda _: None, client_factory=factory,
        health_reader=lambda: dict(generated_at=NOW.isoformat(),
                                   status='PASS', issues=[]),
        environ=ENV)
    assert result['status'] == 'BLOCKED'
    assert result['errors'] == ['FIXTURE_DISCOVERY_WINDOW_STILL_TRUNCATED']
    assert result['historical_requests'] == 0
    assert result['fixture_discovery_requests'] <= 6
    assert not (tmp_path / runner.CACHE /
                'fixture_discovery_receipts/2026-09-04.json').exists()
