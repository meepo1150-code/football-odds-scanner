"""Regression for the real 17 Oct 18:28 failure and immutable growing history."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from odds_scanner.historical_manual import current_account, planner, runner
from odds_scanner.historical_manual.safety import StopPilot, digest
from test_manual_historical import args, native, source, payload, account_payload, ENV

NOW = datetime(2026, 10, 17, 11, 28, tzinfo=timezone.utc)


def options(**changes):
    return args(start_day='2026-10-17', end_day='2026-10-17', times='18:00',
                mode='recover', confirm_live_requests=True, allow_growing_history=True,
                **changes)


def setup(root):
    source(root, [native(kickoff='2026-10-17T14:00:00+00:00',
                         football_day='2026-10-17', observed_at='2026-10-17T10:00:00+00:00')])


def body():
    return json.loads(json.dumps(payload()).replace('2026-09-14', '2026-10-17').replace('16:59', '12:59'))


def execute(root, opts=None, now=NOW, status=200, data=None):
    calls = []
    def factory(key):
        def call(path, params):
            calls.append((key, path))
            value = account_payload(key) if path == '/account' else (data or body())
            if path != '/account' and not data:
                for book in value['bookmakers'].values():
                    for market in book['markets'].values():
                        for outcome in market['outcomes'].values():
                            for player, ticks in outcome['players'].items():
                                outcome['players'][player] = [t for t in ticks if planner.stamp(t['createdAt']) <= now]
            return (200 if path == '/account' else status), {}, json.dumps(value).encode()
        return call
    report = runner.execute(opts or options(), root=root, clock=lambda: now,
        sleeper=lambda _: None, client_factory=factory, environ=ENV,
        health_reader=lambda: dict(generated_at=now.isoformat(), status='PASS', issues=[]))
    return report, calls


def test_past_target_before_kickoff_recovers_instead_of_blocking_entire_day(tmp_path):
    setup(tmp_path)
    report, calls = execute(tmp_path)
    assert report['status'] == 'COMPLETED'
    assert report['historical_requests'] == 1
    assert report['slot_status_counts'] == {'BALANCED_LINE': 1}
    slot = report['results'][0]['slots'][0]
    assert slot['target_thai'] == '2026-10-17T18:00:00+07:00'
    assert slot['selected']['quotes']['home']['quote_at_utc'] == '2026-10-17T10:59:00+00:00'
    assert [p for _, p in calls].count('/historical-odds') == 1
    candidate = json.loads((tmp_path/runner.OUT/'manifest.json').read_text())['candidates'][0]
    assert runner.cache_read(tmp_path/runner.CACHE, candidate) is None  # Legacy callers stay strict.
    replay, calls = execute(tmp_path)
    assert replay['status'] == 'COMPLETED' and replay['cache_hits'] == 1
    assert calls == []


def test_later_target_gets_new_immutable_revision_then_replays_without_http(tmp_path):
    setup(tmp_path)
    first, _ = execute(tmp_path)
    cache = tmp_path/runner.CACHE
    index = next((cache/'cache').glob('*.json'))
    original = index.read_bytes()
    before_raw = {p.name: p.read_bytes() for p in (cache/'raw').glob('*.json')}
    later = options()
    later.times = '20:00'
    later_now = datetime(2026, 10, 17, 13, 28, tzinfo=timezone.utc)
    incomplete, calls = execute(tmp_path, copy.copy(later), later_now)
    assert incomplete['status'] == 'COMPLETED'  # A real new target needs one fetch.
    assert incomplete['historical_requests'] == 1
    assert incomplete['slot_status_counts'] == {'BALANCED_LINE': 1}
    assert index.read_bytes() == original
    assert all((cache/'raw'/name).read_bytes() == raw for name, raw in before_raw.items())
    revisions = list((cache/'cache'/'revisions').glob('*/*.json'))
    assert len(revisions) == 1
    assert len(list((cache/'raw').glob('*.json'))) == 2
    archived = tmp_path/runner.OUT/'new_cache'/revisions[0].relative_to(cache)
    assert archived.read_bytes() == revisions[0].read_bytes()
    replay, calls = execute(tmp_path, later, later_now)
    assert replay['status'] == 'COMPLETED' and replay['cache_hits'] == 1 and not calls
    from odds_scanner.historical_manual.seed import seed
    restored = tmp_path/'restored'
    seed(tmp_path/runner.OUT/'new_cache', restored)
    candidate = json.loads((tmp_path/runner.OUT/'manifest.json').read_text())['candidates'][0]
    assert runner.cache_read(restored, candidate, allow_growing=True) is not None
    assert len(list((restored/'cache'/'revisions').glob('*/*.json'))) == 1


def test_old_growing_cache_is_miss_for_later_target_without_live_permission(tmp_path):
    setup(tmp_path)
    execute(tmp_path)
    opts = options()
    opts.mode, opts.times, opts.confirm_live_requests = 'cache-only', '20:00', False
    report, calls = execute(tmp_path, opts, datetime(2026, 10, 17, 13, 28, tzinfo=timezone.utc))
    assert report['status'] == 'PARTIAL_CACHE_MISS' and not calls
    assert report['slot_status_counts'] == {'CACHE_MISS_NO_REQUEST': 1}


def test_growing_404_does_not_become_permanent_for_later_requested_time(tmp_path):
    setup(tmp_path)
    first, _ = execute(tmp_path, status=404)
    assert first['slot_status_counts'] == {'NO_HISTORICAL_DATA': 1}
    repeat, calls = execute(tmp_path, status=404)
    assert repeat['historical_requests'] == 0 and not calls
    opts = options()
    opts.times = '20:00'
    later, calls = execute(tmp_path, opts, datetime(2026, 10, 17, 13, 28, tzinfo=timezone.utc))
    assert later['historical_requests'] == 1
    assert [p for _, p in calls].count('/historical-odds') == 1


def test_corrupt_revision_fails_closed_without_recollecting(tmp_path):
    setup(tmp_path)
    execute(tmp_path)
    opts = options()
    opts.times = '20:00'
    now = datetime(2026, 10, 17, 13, 28, tzinfo=timezone.utc)
    execute(tmp_path, opts, now)
    index = next((tmp_path/runner.CACHE/'cache'/'revisions').glob('*/*.json'))
    receipt = json.loads(index.read_text())
    (tmp_path/runner.CACHE/'raw'/(receipt['raw_sha256']+'.json')).write_text('{}')
    report, calls = execute(tmp_path, opts, now)
    assert report['errors'] == ['CACHE_HASH_MISMATCH'] and calls == []


def test_legacy_finalized_only_policy_is_not_relaxed(tmp_path):
    setup(tmp_path)
    opts = options()
    opts.allow_growing_history = False
    report, calls = execute(tmp_path, opts)
    assert report['errors'] == ['FIXTURE_HAS_NOT_KICKED_OFF'] and not calls


def test_future_target_explains_the_input_error_without_http(tmp_path):
    setup(tmp_path)
    opts = options()
    opts.times = '21:00'
    report, calls = execute(tmp_path, opts)
    assert report['errors'] == ['TARGETS_MUST_BE_IN_THE_PAST'] and not calls


def test_non_prematch_slots_keep_identity_for_safe_noop_publication(tmp_path):
    from scripts.publish_manual_historical import produce
    setup(tmp_path)
    opts = options()
    opts.times = '21:00'
    report, calls = execute(tmp_path, opts, datetime(2026, 10, 17, 15, tzinfo=timezone.utc))
    assert report['status'] == 'COMPLETED' and not calls
    assert report['slot_status_counts'] == {'NOT_PREMATCH_SLOT': 1}
    manifest = json.loads((tmp_path/runner.OUT/'manifest.json').read_text())
    incoming, counts = produce(report, manifest, [native(kickoff='2026-10-17T14:00:00+00:00')])
    assert incoming == {} and counts == {'NOT_PREMATCH_SLOT': 1}


@pytest.mark.parametrize('fingerprint,probed_at,expected', [
    (digest('test-historical'), NOW.isoformat(), 'SHARED_CURRENT_SCAN_SUBSCRIPTION'),
    (digest('current-manual'), '2026-10-17T10:00:00+00:00', 'CURRENT_SCAN_ACCOUNT_PROBE_INVALID_OR_STALE'),
])
def test_actual_current_account_isolation_blocks_unsafe_or_stale_probe(tmp_path, fingerprint, probed_at, expected):
    setup(tmp_path)
    opts = options()
    opts.current_scan_fingerprint, opts.current_scan_probed_at = fingerprint, probed_at
    report, calls = execute(tmp_path, opts)
    assert expected in report['errors']
    assert not any(p == '/historical-odds' for _, p in calls)


def test_distinct_actual_manual_subscription_allows_history_and_counts_probe(tmp_path):
    setup(tmp_path)
    opts = options()
    opts.current_scan_fingerprint, opts.current_scan_probed_at = digest('current-manual'), NOW.isoformat()
    report, _ = execute(tmp_path, opts)
    assert report['status'] == 'COMPLETED'
    assert report['current_scan_isolation'] == 'DISTINCT_ACTIVE_SUBSCRIPTIONS_VERIFIED'
    assert report['external_account_requests'] == 1 and report['total_http_requests'] == 7


def test_current_probe_uses_only_account_and_returns_no_credential():
    calls = []
    def factory(key):
        def call(path, params):
            calls.append(path)
            return 200, {}, json.dumps(account_payload(key)).encode()
        return call
    result = current_account.probe('private-current-key', client_factory=factory, now=NOW)
    assert calls == ['/account']
    assert result == {'fingerprint': digest('private-current-key'), 'probed_at': NOW.isoformat()}
    assert 'private-current-key' not in json.dumps(result)


def test_runtime_budget_stops_before_next_request_and_keeps_completed_cache(tmp_path):
    from datetime import timedelta
    setup(tmp_path)
    row = json.loads((tmp_path/planner.SOURCES[0]).read_text())
    source(tmp_path, [row, {**row, 'fixture_id': 'id124'}])
    opts = options()
    opts.max_runtime_seconds = 5
    current = [NOW]
    calls = []
    def factory(key):
        def call(path, params):
            calls.append(path)
            value = account_payload(key)
            if path == '/historical-odds':
                value = body()
                value['fixtureId'] = params['fixtureId']
                current[0] += timedelta(seconds=10)
            return 200, {}, json.dumps(value).encode()
        return call
    report = runner.execute(opts, root=tmp_path, clock=lambda: current[0],
        sleeper=lambda _: None, client_factory=factory, environ=ENV,
        health_reader=lambda: dict(generated_at=current[0].isoformat(), status='PASS', issues=[]))
    assert report['status'] == 'STOPPED'
    assert report['errors'] == ['MANUAL_RUNTIME_BUDGET_REACHED_REUSE_SAVED_CACHE']
    assert calls.count('/historical-odds') == 1
    assert len(list((tmp_path/runner.CACHE/'cache').glob('*.json'))) == 1
    assert len(report['results']) == 1


def test_historical_workflow_checks_actual_current_key_without_environment_override():
    workflow = yaml.safe_load(Path('.github/workflows/manual-historical-scan.yml').read_text())
    probe = workflow['jobs']['current_account']
    assert 'environment' not in probe
    step = next(s for s in probe['steps'] if s.get('id') == 'current')
    assert step['env']['CURRENT_SCAN_KEY'] == '${{ secrets.HISTORICAL_ODDSPAPI_KEY }}'
    assert step['if'] == '${{ inputs.mode == \'recover\' && inputs.confirm_live_requests }}'
    historical = workflow['jobs']['historical']
    assert historical['needs'] == 'current_account'
    command = next(s['run'] for s in historical['steps'] if s.get('name', '').startswith('Plan or recover'))
    assert '--allow-growing-history' in command and '--current-scan-fingerprint' in command
    publication = next(s['run'] for s in workflow['jobs']['publish']['steps'] if s.get('name', '').startswith('Commit data'))
    assert 'for attempt in 1 2 3' in publication
    assert publication.index('git reset --hard origin/main') < publication.index('python scripts/publish_manual_historical.py')
    assert 'historical_manual.runner' not in publication
