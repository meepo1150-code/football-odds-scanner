import argparse
import copy
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from odds_scanner.historical_manual import planner, runner
from odds_scanner.historical_manual.safety import StopPilot, digest
from odds_scanner.historical_manual.seed import seed

NOW = datetime(2026, 10, 16, 6, tzinfo=timezone.utc)


def args(**kw):
    return argparse.Namespace(**dict(dict(start_day='2026-09-14', end_day='2026-09-14',
        times='15:00,18:00,21:00,00:00', bookmakers='pinnacle', mode='plan',
        max_requests=25, confirm_live_requests=False), **kw))


def native(fid='id123', **kw):
    return dict(dict(fixture_id=fid, bookmaker='pinnacle', home='Home', away='Away',
        league='League', kickoff='2026-09-14T20:00:00+00:00',
        observed_at='2026-09-14T14:00:00+00:00', football_day='2026-09-14',
        source_semantics='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED',
        ah=dict(home_line=-6, home_price=2, away_price=2)), **kw)


def source(root, rows):
    p = root/planner.SOURCES[0]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return p


def payload(fid='id123', price=2):
    ticks = [dict(createdAt='2026-09-14T'+t+':00+00:00', price=price, active=True)
             for t in ('07:59', '10:59', '13:59', '16:59')]
    return dict(fixtureId=fid, bookmakers={'pinnacle': {'markets': {'1024': {'outcomes': {
        '1024': {'players': {'0': ticks}}, '1025': {'players': {'0': copy.deepcopy(ticks)}}}}}}})


def candidate(root):
    return planner.build(root, '2026-09-14', '2026-09-14', '15:00,18:00,21:00,00:00', 'pinnacle', NOW)['candidates'][0]


def cached(root, c, status=200, body=None):
    runner.cache_store(root/runner.CACHE, c, status, json.dumps(body or payload()).encode(), NOW)


@pytest.mark.parametrize('kickoff,expected', [
    ('2026-09-14T18:45:00Z', '2026-09-14'),  # 15th 01:45 BKK
    ('2026-09-14T22:59:59Z', '2026-09-14'),
    ('2026-09-14T23:00:00Z', '2026-09-15'),
    ('2026-09-15T01:45:00+07:00', '2026-09-14'),
    ('2026-10-01T00:00:00+07:00', '2026-09-30'),
    ('2027-01-01T05:59:59+07:00', '2026-12-31'),
])
def test_football_day_boundaries(kickoff, expected):
    assert planner.football_day(kickoff).isoformat() == expected


def test_thai_targets_to_utc_and_calendar_rollover():
    day = date(2026, 9, 14)
    times = planner.parse_times('01:45,21:00,05:59,00:00,06:00,15:00')
    targets = [planner.target(day, t) for t in times]
    assert [t.isoformat() for t in targets] == [
        '2026-09-14T06:00:00+07:00', '2026-09-14T15:00:00+07:00',
        '2026-09-14T21:00:00+07:00', '2026-09-15T00:00:00+07:00',
        '2026-09-15T01:45:00+07:00', '2026-09-15T05:59:00+07:00']
    assert planner.stamp(targets[4].isoformat()).isoformat() == '2026-09-14T18:45:00+00:00'


@pytest.mark.parametrize('times', ['24:00', '1:45', '15:60', '15:00,15:00', '', '$(bad)', '15:00Z'])
def test_bad_times(times):
    with pytest.raises(ValueError):
        planner.parse_times(times)


@pytest.mark.parametrize('start,end', [('2026-09-15', '2026-09-14'), ('2026-09-01', '2026-09-08'),
    ('2026-9-1', '2026-09-01'), ('2026-02-30', '2026-03-01')])
def test_bad_ranges(start, end):
    with pytest.raises(ValueError):
        planner.parse_days(start, end)


def test_plan_exact_evidence_dedup_no_http(tmp_path):
    source(tmp_path, [native(), native(), native('wrong', source_semantics='OTHER_PROVIDER'),
        native('id999', data_origin='BACKFILLED')])
    r = runner.execute(args(), root=tmp_path, clock=lambda: NOW,
                       client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert r['status'] == 'PLANNED'
    assert r['plan']['planned_historical_requests'] == 1
    assert r['total_http_requests'] == 0
    c = json.loads((tmp_path/runner.OUT/'manifest.json').read_text())['candidates'][0]
    assert len(c['evidence']) == 2
    assert c['targets'][-1]['target_thai'] == '2026-09-15T00:00:00+07:00'
    assert c['targets'][-1]['target_utc'] == '2026-09-14T17:00:00+00:00'
    assert set(c['request']['params']) == {'fixtureId', 'bookmakers'}


def test_mapping_conflict_fails_closed(tmp_path):
    source(tmp_path, [native(), native(home='Wrong')])
    with pytest.raises(ValueError, match='EXACT_IDENTITY_CONFLICT'):
        candidate(tmp_path)


def test_kickoff_day_not_collection_day_and_label_conflict_reported(tmp_path):
    source(tmp_path, [native(football_day='2026-09-15', observed_at='2026-09-10T10:00:00Z')])
    c = candidate(tmp_path)
    assert c['football_day'] == '2026-09-14'
    assert c['source_day_conflict'] is True


def test_future_target_rejected(tmp_path):
    with pytest.raises(ValueError, match='TARGETS_MUST_BE_IN_THE_PAST'):
        planner.build(tmp_path, '2026-10-16', '2026-10-16', '15:00', 'pinnacle', NOW)


def test_cache_only_four_slots_and_original_timestamps(tmp_path):
    source(tmp_path, [native()])
    cached(tmp_path, candidate(tmp_path))
    r = runner.execute(args(mode='cache-only'), root=tmp_path, clock=lambda: NOW,
                       client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert r['status'] == 'COMPLETED'
    assert r['total_http_requests'] == 0
    assert r['cache_hits'] == 1
    assert r['slot_status_counts'] == {'BALANCED_LINE': 4}
    selected = r['results'][0]['slots'][0]['selected']
    assert selected['quotes']['home']['quote_at_utc'] == '2026-09-14T07:59:00+00:00'
    assert selected['official_mainline_verified'] is False
    assert r['results'][0]['original_comparisons']


def test_cache_miss_is_not_no_provider_history(tmp_path):
    source(tmp_path, [native()])
    r = runner.execute(args(mode='cache-only'), root=tmp_path, clock=lambda: NOW)
    assert r['status'] == 'PARTIAL_CACHE_MISS'
    assert r['slot_status_counts'] == {'CACHE_MISS_NO_REQUEST': 4}
    assert r['total_http_requests'] == 0


def test_cap_checked_before_accounts(tmp_path):
    source(tmp_path, [native()])
    r = runner.execute(args(mode='recover', max_requests=0, confirm_live_requests=True),
        root=tmp_path, clock=lambda: NOW, client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert r['errors'] == ['REQUEST_CAP_EXCEEDED_NO_REQUESTS_SENT']
    assert r['total_http_requests'] == 0


def test_corrupt_cache_rejected(tmp_path):
    source(tmp_path, [native()])
    c = candidate(tmp_path)
    cached(tmp_path, c)
    index = tmp_path/runner.CACHE/'cache'/(digest(c['request'])+'.json')
    receipt = json.loads(index.read_text())
    (tmp_path/runner.CACHE/'raw'/(receipt['raw_sha256']+'.json')).write_text('{}')
    with pytest.raises(StopPilot, match='CACHE_HASH_MISMATCH'):
        runner.cache_read(tmp_path/runner.CACHE, c)


ENV = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/heads/main',
           PILOT_ENVIRONMENT='historical-research', HISTORICAL_ODDSPAPI_KEY='test-historical',
           ACCOUNT_PROBE_KEY='test-production')


def account_payload(key):
    return dict(current_subscription_id=key, subscriptions=[dict(subscription_id=key,
        is_active=True, request_limit=250, request_count=0, sport_ids=[10], bookmakers={'pinnacle': {}})])


def live(tmp_path, *, status=200, body=None, env=None, now=NOW, rows=None):
    source(tmp_path, rows or [native()])
    calls = []
    def factory(key):
        def request(path, params):
            calls.append((key, path, params))
            value = account_payload(key) if path == '/account' else (body or payload(params['fixtureId']))
            return (200 if path == '/account' else status), {}, json.dumps(value).encode()
        return request
    r = runner.execute(args(mode='recover', confirm_live_requests=True), root=tmp_path,
        clock=lambda: now, sleeper=lambda _: None, client_factory=factory,
        health_reader=lambda: dict(generated_at=now.isoformat(), status='PASS', issues=[]),
        environ=ENV if env is None else env)
    return r, calls


def test_live_one_request_supplies_four_rounds_with_separate_keys(tmp_path):
    r, calls = live(tmp_path)
    assert r['status'] == 'COMPLETED'
    assert (r['historical_requests'], r['account_requests'], r['total_http_requests']) == (1, 5, 6)
    assert r['slot_status_counts'] == {'BALANCED_LINE': 4}
    history = [c for c in calls if c[1] == '/historical-odds']
    assert history == [('test-historical', '/historical-odds', {'fixtureId':'id123', 'bookmakers':'pinnacle'})]
    assert r['production_before'] == r['production_after']


def test_429_stops_no_retry(tmp_path):
    r, calls = live(tmp_path, status=429, rows=[native(), native('id124')])
    assert r['status'] == 'STOPPED'
    assert r['historical_requests'] == 1
    assert sum(c[1] == '/historical-odds' for c in calls) == 1
    assert not list((tmp_path/runner.CACHE/'cache').glob('*.json'))


def test_quality_anomaly_stops_before_next_request(tmp_path):
    r, _ = live(tmp_path, body=payload(price=0), rows=[native(), native('id124')])
    assert r['errors'] == ['QUOTE_QUALITY_ANOMALY']
    assert r['historical_requests'] == 1


def test_404_negative_cache_not_retried(tmp_path):
    r, _ = live(tmp_path, status=404)
    assert r['status'] == 'COMPLETED'
    assert r['slot_status_counts'] == {'NO_HISTORICAL_DATA': 4}
    r = runner.execute(args(mode='recover'), root=tmp_path, clock=lambda: NOW,
                       client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert r['status'] == 'COMPLETED'
    assert r['total_http_requests'] == 0


@pytest.mark.parametrize('env', [dict(ENV, GITHUB_REF='refs/heads/other'),
    dict(ENV, GITHUB_EVENT_NAME='push'), dict(ENV, PILOT_ENVIRONMENT='other')])
def test_live_context_gate(tmp_path, env):
    r, calls = live(tmp_path, env=env)
    assert r['status'] == 'BLOCKED'
    assert not calls


def test_shared_subscription_gate(tmp_path):
    r, calls = live(tmp_path, env=dict(ENV, ACCOUNT_PROBE_KEY='test-historical'))
    assert 'SHARED_PRODUCTION_SUBSCRIPTION' in r['errors']
    assert not any(c[1] == '/historical-odds' for c in calls)


def test_production_quiet_window_stops_before_http(tmp_path):
    r, calls = live(tmp_path, now=datetime(2026, 10, 16, 8, tzinfo=timezone.utc))
    assert r['errors'] == ['PRODUCTION_QUIET_WINDOW_CLOSED']
    assert not calls


def test_kickoff_exclusion(tmp_path):
    source(tmp_path, [native(kickoff='2026-09-14T17:00:00Z')])
    cached(tmp_path, candidate(tmp_path))
    r = runner.execute(args(mode='cache-only'), root=tmp_path, clock=lambda: NOW)
    assert r['slot_status_counts'] == {'BALANCED_LINE': 3, 'NOT_PREMATCH_SLOT': 1}


def test_latest_inactive_never_rolls_back(tmp_path):
    source(tmp_path, [native()])
    body = payload()
    body['bookmakers']['pinnacle']['markets']['1024']['outcomes']['1024']['players']['0'].append(
        dict(createdAt='2026-09-14T08:00:00Z', price=2, active=False))
    cached(tmp_path, candidate(tmp_path), body=body)
    r = runner.execute(args(mode='cache-only'), root=tmp_path, clock=lambda: NOW)
    assert r['results'][0]['slots'][0]['status'] == 'MAINLINE_UNRESOLVED'


def test_seed_reuses_hash_verified_cache(tmp_path):
    original = tmp_path/'old'
    source(original, [native()])
    c = candidate(original)
    cached(original, c)
    destination = tmp_path/'new'
    seed(original, destination)
    assert runner.cache_read(destination, c) == payload()


def test_workflow_is_manual_readonly_and_inputs_not_shell_interpolated():
    import yaml
    path = Path('.github/workflows/manual-historical-scan.yml')
    workflow = yaml.safe_load(path.read_text())
    trigger = workflow.get('on', workflow.get(True))
    assert set(trigger) == {'workflow_dispatch'}
    assert workflow['permissions'] == {'contents': 'read', 'actions': 'read'}
    for step in workflow['jobs']['historical']['steps']:
        assert '${{ inputs.' not in step.get('run', '')
    assert workflow['jobs']['historical']['environment'] == 'historical-research'
