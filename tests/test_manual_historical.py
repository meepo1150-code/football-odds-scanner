import argparse
import copy
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from odds_scanner.historical_manual import planner, runner
from odds_scanner.historical_manual.safety import StopPilot, digest, health_check
from odds_scanner.historical_manual.seed import seed

NOW = datetime(2026, 10, 16, 6, tzinfo=timezone.utc)


def args(**kw):
    return argparse.Namespace(**dict(dict(start_day='2026-09-14', end_day='2026-09-14',
        times='15:00,18:00,21:00,00:00', bookmakers='pinnacle', mode='plan',
        confirm_live_requests=False), **kw))


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


def test_live_confirmation_still_required_without_count_cap(tmp_path):
    source(tmp_path, [native()])
    r = runner.execute(args(mode='recover', confirm_live_requests=False),
        root=tmp_path, clock=lambda: NOW, client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert r['errors'] == ['LIVE_REQUEST_CONFIRMATION_REQUIRED']
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


def live(tmp_path, *, status=200, body=None, env=None, now=NOW, rows=None,
         health_reader=None, production_delta=0):
    source(tmp_path, rows or [native()])
    calls = []
    def factory(key):
        def request(path, params):
            calls.append((key, path, params))
            value = account_payload(key) if path == '/account' else (body or payload(params['fixtureId']))
            if path == '/account' and key == 'test-production' and sum(
                    k == key and p == '/account' for k, p, _ in calls) > 1:
                value['subscriptions'][0]['request_count'] = production_delta
            return (200 if path == '/account' else status), {}, json.dumps(value).encode()
        return request
    r = runner.execute(args(mode='recover', confirm_live_requests=True), root=tmp_path,
        clock=lambda: now, sleeper=lambda _: None, client_factory=factory,
        health_reader=health_reader or (lambda: dict(generated_at=now.isoformat(), status='PASS', issues=[])),
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


def test_more_than_fifty_uncached_candidates_are_all_processed(tmp_path):
    # Injected transport only: prove no count-based cutoff without provider HTTP.
    rows = [native('id'+str(1000+i)) for i in range(51)]
    r, calls = live(tmp_path, rows=rows)
    assert r['status'] == 'COMPLETED'
    assert r['historical_requests'] == 51
    assert r['account_requests'] == 105
    assert len(r['results']) == 51
    assert r['slot_status_counts'] == {'BALANCED_LINE': 204}
    sent = [p['fixtureId'] for _, path, p in calls if path == '/historical-odds']
    assert len(sent) == len(set(sent)) == 51
    assert r['plan']['request_count_policy'] == 'ALL_VERIFIED_CANDIDATES_NO_INTERNAL_COUNT_CAP'
    assert 'max_new_historical_requests' not in r['plan']


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


@pytest.mark.parametrize('hour,minute', [(8, 0), (11, 37), (14, 0), (17, 0)])
def test_distinct_manual_accounts_work_during_production_clock_windows(tmp_path, hour, minute):
    r, calls = live(tmp_path, now=datetime(2026, 10, 16, hour, minute, tzinfo=timezone.utc))
    assert r['status'] == 'COMPLETED'
    assert r['historical_requests'] == 1
    assert r['credential_isolation'] == 'DISTINCT_ACTIVE_SUBSCRIPTIONS_VERIFIED'
    assert r['time_policy'] == 'ISOLATED_MANUAL_NO_PRODUCTION_CLOCK_BLACKOUT'
    assert all(k == 'test-historical' for k, p, _ in calls if p == '/historical-odds')


def test_existing_production_fail_retained_after_isolation_not_relabelled(tmp_path):
    health = dict(generated_at=NOW.isoformat(), status='FAIL', issues=['SCAN_MISSING', 'FT_DELAY'])
    r, _ = live(tmp_path, health_reader=lambda: health)
    assert r['status'] == 'COMPLETED'
    assert r['production_health_baseline'] == health


def test_default_pilot_health_still_rejects_fail():
    health = dict(generated_at=NOW.isoformat(), status='FAIL', issues=['SCAN_MISSING'])
    with pytest.raises(StopPilot, match='PRODUCTION_HEALTH_UNSAFE'):
        health_check(health, health, NOW)
    with pytest.raises(StopPilot, match='CREDENTIAL_ISOLATION_UNVERIFIED'):
        health_check(health, health, NOW, account_isolation=dict(research='a'*64, production='a'*64))


@pytest.mark.parametrize('baseline_status,current_status,reason', [
    ('PASS', 'FAIL', 'PRODUCTION_HEALTH_DEGRADED'),
    ('FAIL', 'FAIL', 'NEW_PRODUCTION_HEALTH_ISSUE'),
])
def test_new_production_health_problem_stops_before_history(tmp_path, baseline_status, current_status, reason):
    baseline = dict(generated_at=NOW.isoformat(), status=baseline_status, issues=[])
    current = dict(generated_at=NOW.isoformat(), status=current_status, issues=['NEW_PROBLEM'])
    readings = iter([baseline, current])
    r, calls = live(tmp_path, health_reader=lambda: next(readings))
    assert r['errors'] == [reason]
    assert not any(p == '/historical-odds' for _, p, _ in calls)


def test_stale_health_still_blocks_with_isolated_accounts(tmp_path):
    health = dict(generated_at='2026-10-16T05:00:00Z', status='FAIL', issues=[])
    r, calls = live(tmp_path, health_reader=lambda: health)
    assert r['errors'] == ['PRODUCTION_HEALTH_STALE']
    assert not any(p == '/historical-odds' for _, p, _ in calls)


def test_concurrent_production_usage_is_reported_without_false_attribution(tmp_path):
    r, calls = live(tmp_path, production_delta=1)
    assert r['status'] == 'COMPLETED'
    assert r['production_quota_delta'] == 1
    assert r['production_before']['request_count'] == 0
    assert r['production_after']['request_count'] == 1
    assert 'NOT_ATTRIBUTED_TO_HISTORICAL' in r['production_usage_attribution']
    assert all(p == '/account' for k, p, _ in calls if k == 'test-production')


def test_checkout_production_sources_not_mutated(tmp_path):
    source(tmp_path, [native()])
    before = (tmp_path/planner.SOURCES[0]).read_bytes()
    r, _ = live(tmp_path)
    assert r['status'] == 'COMPLETED'
    assert (tmp_path/planner.SOURCES[0]).read_bytes() == before


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
    assert 'max_new_requests' not in trigger['workflow_dispatch']['inputs']
    assert '--max-requests' not in path.read_text()
    assert workflow['permissions'] == {'contents': 'read', 'actions': 'read'}
    for step in workflow['jobs']['historical']['steps']:
        assert '${{ inputs.' not in step.get('run', '')
    assert workflow['jobs']['historical']['environment'] == 'historical-research'
    assert any(s.get('run') == 'git diff --exit-code -- data reports config'
               and s.get('if') == 'always()' for s in workflow['jobs']['historical']['steps'])


def test_external_verified_fixture_before_first_live_scan(tmp_path):
    p = tmp_path / planner.EXTERNAL_FIXTURE_SOURCE
    p.parent.mkdir(parents=True, exist_ok=True)
    row = dict(fixture_id='id987654', bookmaker='pinnacle',
        home='Historical Home', away='Historical Away', league='Verified League',
        kickoff='2026-09-13T15:00:00Z', football_day='2026-09-13',
        mapping_source='ODDSPAPI_EXTERNALPROVIDERS_EXACT_IDS',
        evidence_url='https://example.org/verified/fixture/987654')
    p.write_text(json.dumps(row) + '\n')
    manifest = planner.build(tmp_path, '2026-09-13', '2026-09-13',
        '15:00,18:00,21:00,00:00', 'pinnacle', NOW)
    assert manifest['unique_fixtures'] == 1
    assert manifest['candidates'][0]['fixture_id'] == 'id987654'
    assert manifest['candidates'][0]['observations'] == []
    result = runner.execute(args(start_day='2026-09-13', end_day='2026-09-13'),
        root=tmp_path, clock=lambda: NOW,
        client_factory=lambda *_: pytest.fail('HTTP forbidden'))
    assert result['status'] == 'PLANNED'
    assert result['plan']['planned_historical_requests'] == 1
    assert result['total_http_requests'] == 0


def test_external_fixture_rejects_incorrect_football_day(tmp_path):
    p = tmp_path / planner.EXTERNAL_FIXTURE_SOURCE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(fixture_id='id987654', bookmaker='pinnacle',
        home='Home', away='Away', league='League',
        kickoff='2026-09-13T15:00:00Z', football_day='2026-09-12',
        mapping_source='ODDSPAPI_EXACT', evidence_url='https://example.org/evidence')) + '\n')
    with pytest.raises(ValueError, match='EXTERNAL_FOOTBALL_DAY_CONFLICT'):
        planner.build(tmp_path, '2026-09-13', '2026-09-13',
            '15:00', 'pinnacle', NOW)


def test_publish_new_verified_fixture_without_original_snapshot():
    from scripts.publish_manual_historical import produce
    c = dict(fixture_id='id987654', bookmaker='pinnacle', home='Home', away='Away',
        league='League', kickoff='2026-09-13T15:00:00Z', football_day='2026-09-13',
        evidence=[dict(mapping_source='ODDSPAPI_EXACT',
                       evidence_url='https://example.org/verified')],
        targets=[dict(target_utc='2026-09-13T08:00:00Z')])
    s = dict(line_selection='BALANCED_LINE', market='AH',
        official_mainline_verified=False, fixture_id=c['fixture_id'],
        bookmaker='pinnacle', slot_utc='2026-09-13T08:00:00Z',
        market_id='market-1', home_line=-0.5, away_line=0.5,
        raw_record_hash='sha256-test',
        quotes={side: dict(active=True, price=2.0,
            quote_at_utc='2026-09-13T07:59:00Z') for side in ('home', 'away')})
    manifest=dict(scope='VERIFIED_NATIVE_OR_EXTERNAL_ODDSPAPI_FIXTURES', candidates=[c])
    report=dict(status='COMPLETED', errors=[], production_writes=0, research_only=True,
        results=[dict(fixture_id=c['fixture_id'], bookmaker='pinnacle',
            football_day=c['football_day'], home='Home', away='Away',
            kickoff=c['kickoff'], slots=[dict(target_utc='2026-09-13T08:00:00Z',
                status='BALANCED_LINE', selected=s)])])
    incoming, counts = produce(report, manifest, [])
    assert len(incoming) == 1
    row = next(iter(incoming.values()))
    assert row['favorite_side'] == 'H'
    assert row['favorite_side_basis'] == 'HISTORICAL_NEGATIVE_AH_HANDICAP'
    assert row['data_origin'] == 'BACKFILLED'
    assert row['promotion_eligible'] is False
    assert row['observed_at'] == '2026-09-13T07:59:00+00:00'


def test_native_schedule_receipt_discovers_historical_fixture_without_snapshot(tmp_path, monkeypatch):
    from odds_scanner import master_schedule_plan
    monkeypatch.setattr(master_schedule_plan, 'registry', lambda: [
        dict(tournament_id=17, tournament_name='Verified League')])
    path = tmp_path/'data/normalized/research_v2_provider_responses.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(provider='oddspapi', endpoint='/fixtures',
        response_id='immutable-response-id', observed_at='2026-09-14T00:00:00Z',
        payload=[dict(fixtureId='id987654', tournamentId=17,
            participant1Name='Home', participant2Name='Away',
            startTime='2026-09-13T15:00:00Z')])) + '\n')
    manifest = planner.build(tmp_path, '2026-09-13', '2026-09-13',
        '15:00,18:00,21:00,00:00', 'pinnacle', NOW)
    assert manifest['unique_fixtures'] == 1
    c = manifest['candidates'][0]
    assert c['observations'] == []
    assert c['evidence'][0]['mapping_source'] == 'ODDSPAPI_NATIVE_FIXTURES_RECEIPT'
    assert c['evidence'][0]['response_id'] == 'immutable-response-id'

def test_publish_native_observation_source_without_published_snapshot():
    from scripts.publish_manual_historical import produce
    c = dict(fixture_id='id123', bookmaker='pinnacle', home='Home',
        away='Away', league='League', kickoff='2026-09-13T15:00:00Z',
        football_day='2026-09-13',
        observations=[dict(fixture_id='id123', source_semantics='CURRENT_ODDSPAPI_MAINLINE')],
        evidence=[dict(path='data/research/pre_sep14_historical_originals.jsonl',
                       line=1, sha256='a'*64)],
        targets=[dict(target_utc='2026-09-13T08:00:00Z')])
    selection = dict(line_selection='BALANCED_LINE', market='AH',
        official_mainline_verified=False, fixture_id='id123',
        bookmaker='pinnacle', slot_utc='2026-09-13T08:00:00Z',
        market_id='ah-1', home_line=-0.5, away_line=0.5,
        quotes={side:dict(active=True,price=2.0,
            quote_at_utc='2026-09-13T07:59:00Z') for side in ('home','away')})
    manifest=dict(scope='VERIFIED_NATIVE_OR_EXTERNAL_ODDSPAPI_FIXTURES',
        candidates=[c])
    report=dict(status='COMPLETED', errors=[], production_writes=0,
        research_only=True, results=[dict(
            fixture_id='id123', bookmaker='pinnacle', home='Home',
            away='Away', kickoff=c['kickoff'], football_day=c['football_day'],
            slots=[dict(target_utc='2026-09-13T08:00:00Z',
                        status='BALANCED_LINE', selected=selection)])])
    incoming, counts=produce(report,manifest,[])
    assert len(incoming)==1
    assert counts['BALANCED_LINE']==1
    assert next(iter(incoming.values()))['data_origin']=='BACKFILLED'
